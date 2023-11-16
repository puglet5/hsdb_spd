import json
import logging
from dataclasses import dataclass
from io import BytesIO, StringIO
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd
from celery import shared_task
from dacite import from_dict
from findpeaks import findpeaks
from requests import Response

from app.config.settings import settings
from app.tools.utils import (
    COMMON_RANGE_FREQ_INTERVAL,
    DEGREE,
    FIT_FREQ_INTERVAL,
    SPEED_C,
    URL,
    PeakData,
    ProcessingMessage,
    fft,
    minmax,
    pad,
    timeit,
)

from ..tasks import communication
from ..tasks.communication import update_status
from ..tools.converters import convert_to_csv, download_file, validate_json

logger = logging.getLogger(__name__)

PARENT_MODEL_NAME = settings.db_parent_model


@dataclass
class SpectrumParentModel:
    id: int
    title: str


@dataclass
class Spectrum:
    file_url: URL
    filename: str
    id: int
    parent: SpectrumParentModel
    format: str
    status: str
    category: str
    range: str
    metadata: str | dict | None
    sample_thickness: float | None
    is_reference: bool

    raw_file: BytesIO | None
    processed_file: BytesIO | None
    csv_file: BytesIO | None
    peaks: npt.NDArray[np.float_] | None
    peak_metadata: PeakData | dict[Any, Any] | None

    def __post_init__(self):
        self.file_url = f"{settings.db_url}{self.file_url}"
        self.raw_file = download_file(self.file_url)
        self.to_csv()
        logger.warn(self)

    def to_csv(self) -> BytesIO | None:
        if self.raw_file is None:
            return None
        if isinstance(self.csv_file, BytesIO):
            return self.csv_file

        self.csv_file = convert_to_csv(self.raw_file, self.filename)
        return self.csv_file

    def find_peaks(self) -> npt.NDArray[np.float_] | None:
        """
        Find peaks in a second column of csv-like data and return peaks as a numpy array.

        Peaks are filtered by their rank and height returned by findpeaks.
        Return None if none were found
        """
        if self.csv_file is None:
            return None

        try:
            self.csv_file.seek(0)
            data: npt.NDArray[np.float_] = np.loadtxt(self.csv_file, delimiter=",")[
                :, 1
            ]
            self.csv_file.seek(0)
            fp = findpeaks(
                method="topology",
                scale=False,
                denoise="bilateral",
                lookahead=2,
                interpolate=3,
            )
            if (result := fp.fit(data / np.max(data))) is not None:
                df: pd.DataFrame = result["df"]
            else:
                return None

            filtered_pos: pd.DataFrame | None = df.query(
                "peak == True & rank != 0 & rank <= 40 & y >= 0.005"
            )  # type: ignore
            peaks: npt.NDArray[np.float_] | None = filtered_pos["x"].to_numpy()
            self.peaks = peaks
            return self.peaks
        except Exception as e:
            logger.error(e)
            return None

    def construct_peak_metadata(self) -> PeakData | dict[Any, Any] | None:
        if self.peaks is None:
            return None

        peak_metadata: PeakData = {"peaks": [{"position": i} for i in self.peaks]}
        self.peak_metadata = peak_metadata
        return peak_metadata

    def merge_metadata(self, additional_metadata: dict[Any, Any]) -> dict | None:
        if isinstance(self.metadata, str):
            self.metadata = {**json.loads(self.metadata), **additional_metadata}
        elif isinstance(self.metadata, dict):
            self.metadata = {**self.metadata, **additional_metadata}

        return self.metadata


@dataclass
class THzSpectrum(Spectrum):
    ...


@dataclass
class DatTypeSpectrum(Spectrum):
    ...


@timeit
def process_spectrum(id: int) -> ProcessingMessage:
    """
    Process spectrum with corresponding id and upload resulting file to processed_file in db
    """
    try:
        if (raw_spectrum := communication.get_spectrum(id)) is None:
            update_status.delay(id, "error")
            return {"message": f"Error retrieving spectrum with {id}"}

        update_status.delay(id, "ongoing")

        spectrum = from_dict(
            data_class=Spectrum,
            data={
                **json.loads(raw_spectrum)["spectrum"],
                "parent": json.loads(raw_spectrum)["spectrum"][PARENT_MODEL_NAME],
            },
        )

        logger.warn(spectrum)

        if spectrum.raw_file is None:
            update_status.delay(id, "error")
            return {"message": f"Error getting spectrum file from server"}

        if (spectrum.csv_file) is None:
            update_status.delay(id, "error")
            return {"message": f"Error coverting spectrum with id {id}"}

        if spectrum.category == "thz":
            handle_thz(spectrum)
            return {"message": f"Done processing for thz spectrum with id {id}"}

        spectrum.find_peaks()
        spectrum.construct_peak_metadata()

        file_patch_response: Response | None = communication.patch_with_processed_file(
            id, spectrum.csv_file
        )

        metadata_patch_response: Response | None = None
        if validate_json(spectrum.metadata) and spectrum.peak_metadata is not None:
            spectrum.merge_metadata(spectrum.peak_metadata)  # type:ignore
            if spectrum.metadata is not None:
                metadata_patch_response = communication.update_metadata(
                    id, spectrum.metadata
                )

        if metadata_patch_response is None or file_patch_response is None:
            update_status.delay(id, "error")
            return {
                "message": f"Error uploading processing data to spectrum with id {id}"
            }

        update_status.delay(id, "successful")

        return {"message": f"Done processing for spectrum with id {id}"}
    except Exception as e:
        logger.error(e)
        return {"message": f"Error processing spectrum with id {id}"}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 0},
    name="spectra:process_routine",
)
def process_routine(self, id: int):
    task = process_spectrum(id)
    communication.update_processing_message.delay(
        id, f'[{task.get("execution_time"):.2f} s.] {task["message"]}'
    )
    return task


def process_thz(
    ref_csv: BytesIO, sample_csv: BytesIO, sample_thickness: float
) -> BytesIO | None:
    """
    Extract refraction and absorption index from THz TDS data.

    First file in a `files` tuple must be a reference spectrum.

    Returns n×3 csv data as bytes where columns are frequency in THz, refraction index and absorption index
    """
    try:
        ref_data = pd.read_csv(ref_csv).to_numpy()
        sample_data = pd.read_csv(sample_csv).to_numpy()

        ref_range: npt.NDArray[np.float_] = np.array(list(map(minmax, ref_data.T)))
        sample_range: npt.NDArray[np.float_] = np.array(
            list(map(minmax, sample_data.T))
        )

        ref_area: np.float_ = -np.trapz(*np.flip(ref_data.T))
        sample_area: np.float_ = -np.trapz(*np.flip(sample_data.T))

        scaled_ref_intensity: npt.NDArray[np.float_] = ref_data.T[1] - ref_area / (
            np.sum(np.abs(ref_range))
        )
        scaled_sample_intensity: npt.NDArray[np.float_] = sample_data.T[
            1
        ] - sample_area / (np.sum(np.abs(sample_range)))

        ref_fft = fft(pad(scaled_ref_intensity, 10000))
        sample_fft = fft(pad(scaled_sample_intensity, 10000))

        # TODO: validate sampling interval equality for ref and sample
        sampling_interval = np.diff(np.transpose(ref_data)[0, :2])[0]
        frequency_inc = 1 / (sampling_interval * len(ref_fft))

        frequencies: npt.NDArray[np.float_] = np.arange(
            0, 1 / sampling_interval, frequency_inc
        )

        ref_phase: npt.NDArray[np.float_] = 1 / DEGREE * np.unwrap(np.angle(ref_fft))
        sample_phase: npt.NDArray[np.float_] = (
            1 / DEGREE * np.unwrap(np.angle(sample_fft))
        )

        ref_amplitude: npt.NDArray[np.float_] = 1 / len(ref_fft) * np.abs(ref_fft)
        sample_amplitude: npt.NDArray[np.float_] = (
            1 / len(sample_fft) * np.abs(sample_fft)
        )

        ref_phase_vs_freq = np.array([frequencies, ref_phase]).T
        sample_phase_vs_freq = np.array([frequencies, sample_phase]).T

        fit_freq_mask: npt.NDArray[np.bool_] = np.ma.masked_inside(
            ref_phase_vs_freq[:, 0], *FIT_FREQ_INTERVAL
        ).mask

        ref_phase_to_fit = ref_phase_vs_freq[fit_freq_mask]
        sample_phase_to_fit = sample_phase_vs_freq[fit_freq_mask]

        fit_zero_order_coeffs: npt.NDArray[np.float_] = np.array(
            [
                np.polyfit(*sample_phase_to_fit.T, 1),  # type: ignore
                np.polyfit(*ref_phase_to_fit.T, 1),  # type: ignore
            ]
        )[:, -1]

        sample_phase_shifted: npt.NDArray[np.float_] = (
            sample_phase + np.diff(fit_zero_order_coeffs)[0]
        )

        refraction_index: npt.NDArray[np.float_] = (
            0.3 * (ref_phase - sample_phase_shifted)
        ) / SPEED_C / frequencies / sample_thickness + 1

        range_freq_mask: npt.NDArray[np.bool_] = np.ma.masked_inside(
            ref_phase_vs_freq[:, 0], *COMMON_RANGE_FREQ_INTERVAL
        ).mask

        absorption_index = (
            20
            / sample_thickness
            * np.log(
                (4 * refraction_index * ref_amplitude)
                / ((refraction_index + 1) ** 2 * sample_amplitude)
            )
        )

        data = np.array([frequencies, refraction_index, absorption_index]).T[
            range_freq_mask
        ]
        full_data = pd.DataFrame([*data.T, *sample_data.T]).to_numpy().T

        sio = StringIO()

        np.savetxt(
            sio,
            full_data,
            delimiter=",",
            comments="",
            header="Frequency (THz),Refraction,Absorption(cm^-1),Optical Delay (ps),Signal",
        )

        sio.seek(0)
        bio = BytesIO(sio.read().encode("utf8"))
        sio.close()
        bio.seek(0)

        return bio
    except Exception as e:
        logger.error(e)
        return None


def handle_thz(spectrum: Spectrum):
    id = spectrum.id
    if spectrum.raw_file is None:
        update_status.delay(id, "error")
        return {"message": f"Error processing spectrum with id {id}"}

    ref_id = communication.retrieve_reference_spectrum_id(parent_id=spectrum.parent.id)
    if ref_id is not None:
        raw_ref_spectrum = communication.get_spectrum(int(ref_id))
        if raw_ref_spectrum is None:
            update_status(id, "error")
            return {"message": f"Error retrieving reference spectrum with id {ref_id}"}

        ref_spectrum = from_dict(
            data_class=Spectrum,
            data={
                **json.loads(raw_ref_spectrum)["spectrum"],
                "parent": json.loads(raw_ref_spectrum)["spectrum"][PARENT_MODEL_NAME],
            },
        )
        if (ref_spectrum.raw_file) is None:
            update_status.delay(id, "error")
            return {"message": f"Error getting spectrum file from server"}
        ref_csv = ref_spectrum.to_csv()
        sample_csv = spectrum.to_csv()

        if ref_csv is None or sample_csv is None:
            update_status.delay(id, "error")
            return {"message": f"Error processing spectrum with id {id}"}

        if spectrum.sample_thickness is None:
            update_status.delay(id, "error")
            return {
                "message": f"Error while processing. Sample thickness is not provided"
            }

        if (
            thz_data := process_thz(ref_csv, sample_csv, spectrum.sample_thickness)
        ) is not None:
            thz_data.name = f'{spectrum.filename.rsplit(".", 1)[0]}_processed.csv'
            file_patch_response: Response | None = (
                communication.patch_with_processed_file(id, thz_data)
            )

            if file_patch_response is None:
                update_status.delay(id, "error")
                return {
                    "message": f"Error uploading processing data to spectrum with id {id}"
                }

            update_status.delay(id, "successful")
            return {"message": f"Done processing for spectrum with id {id}"}
        else:
            update_status.delay(id, "error")
            return {"message": f"Error processing spectrum with id {id}"}

    else:
        try:
            if spectrum.csv_file is None:
                update_status.delay(id, "error")
                return {"message": f"Error coverting spectrum with id {id}"}

            file_patch_response: Response | None = (
                communication.patch_with_processed_file(id, spectrum.csv_file)
            )

            if file_patch_response is None:
                update_status.delay(id, "error")
                return {
                    "message": f"Error uploading processing data to spectrum with id {id}"
                }

            update_status.delay(id, "successful")
            return {"message": f"Done processing for spectrum with id {id}"}

        except Exception as e:
            logger.error(e)
            update_status.delay(id, "error")
