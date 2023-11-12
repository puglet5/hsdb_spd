from io import BytesIO
import json
import logging
from typing import TypeAlias, TypedDict, NotRequired, Any
import numpy as np
import numpy.typing as npt
from findpeaks import findpeaks

from celery import shared_task
import numpy as np
import pandas as pd
from requests import Response
from dataclasses import dataclass, field

from app.config.settings import settings

from ..tasks import communication
from ..tasks.communication import update_status
from ..tools.converters import (
    convert_to_csv,
    download_file,
    validate_json,
)

from functools import wraps
import time

URL: TypeAlias = str

logger = logging.getLogger(__name__)


DEGREE = 0.0174533
FIT_FREQ_INTERVAL = (0.1, 0.5)
COMMON_RANGE_FREQ_INTERVAL = (0.2, 1.1)
SPEED_C = 360


def minmax(x):
    return [np.min(x), np.max(x)]


def pad(x, n):
    return np.pad(x, (0, n - len(x)), mode="constant")


def fft(x):
    return np.fft.fft(x)


class PeakDatum(TypedDict):
    position: float
    fwhm: NotRequired[float]


class PeakData(TypedDict):
    peaks: list[PeakDatum]


class ProcessingMessage(TypedDict):
    message: str
    execution_time: NotRequired[float]


def timeit(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        result["execution_time"] = total_time
        return result

    return timeit_wrapper


@dataclass
class Sample:
    id: int
    title: str


@dataclass
class Spectrum:
    file_url: URL
    filename: str
    id: int
    sample: Sample
    format: str
    status: str
    category: str
    range: str
    metadata: str | dict | None
    sample_thickness: float
    is_reference: bool

    raw_file: BytesIO | None = field(init=False, default=None)
    processed_file: BytesIO | None = field(init=False, default=None)
    csv_file: BytesIO | None = field(init=False, default=None)
    peaks: npt.NDArray[np.float_] | None = field(init=False, default=None)
    peak_metadata: PeakData | dict[Any, Any] | None = field(init=False, default=None)

    def __post_init__(self):
        self.sample = Sample(**self.sample)  # type: ignore
        self.file_url = f"{settings.hsdb_url}{self.file_url}"
        self.raw_file = download_file(self.file_url)
        self.to_csv()

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
            fp = findpeaks(method="topology", lookahead=2, denoise="bilateral")
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
    Process spectrum with corresponding id and upload resulting file to processed_file in hsdb
    """
    try:
        if (raw_spectrum := communication.get_spectrum(id)) is None:
            update_status(id, "error")
            return {"message": f"Error retrieving spectrum with {id}"}

        update_status(id, "ongoing")

        spectrum = Spectrum(**json.loads(raw_spectrum)["spectrum"])

        if spectrum.raw_file is None:
            update_status(id, "error")
            return {"message": f"Error getting spectrum file from server"}

        if (spectrum.csv_file) is None:
            update_status(id, "error")
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
            if (
                spectrum.merge_metadata(spectrum.peak_metadata)  # type:ignore
            ) is not None:
                metadata_patch_response = communication.update_metadata(
                    id, spectrum.metadata
                )

        logger.warn([file_patch_response, metadata_patch_response])

        if metadata_patch_response is None or file_patch_response is None:
            update_status(id, "error")
            return {
                "message": f"Error uploading processing data to spectrum with id {id}"
            }

        update_status(id, "successful")

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
    communication.update_processing_message(
        id, f'[{task.get("execution_time"):.2f} s.] {task["message"]}'
    )
    return task


def process_thz(ref_csv: BytesIO, sample_csv: BytesIO, sample_thickness: float):
    """
    Extract refraction and absorption index from THz TDS data.

    First file in a `files` tuple must be a reference spectrum.
    """
    ref_data = pd.read_csv(ref_csv).to_numpy()
    sample_data = pd.read_csv(sample_csv).to_numpy()

    ref_range: npt.NDArray[np.float_] = np.array(list(map(minmax, ref_data.T)))
    sample_range: npt.NDArray[np.float_] = np.array(list(map(minmax, sample_data.T)))

    ref_area: np.float_ = -np.trapz(*np.flip(ref_data.T))
    sample_area: np.float_ = -np.trapz(*np.flip(sample_data.T))

    scaled_ref_intensity: npt.NDArray[np.float_] = ref_data.T[1] - ref_area / (
        np.sum(np.abs(ref_range))
    )
    scaled_sample_intensity: npt.NDArray[np.float_] = sample_data.T[1] - sample_area / (
        np.sum(np.abs(sample_range))
    )

    ref_fft = fft(pad(scaled_ref_intensity, 10000))
    sample_fft = fft(pad(scaled_sample_intensity, 10000))

    # TODO: validate sampling interval equality for ref and sample
    sampling_interval = np.diff(np.transpose(ref_data)[0, :2])[0]
    frequency_inc = 1 / (sampling_interval * len(ref_fft))

    frequencies: npt.NDArray[np.float_] = np.arange(
        0, 1 / sampling_interval, frequency_inc
    )

    ref_phase: npt.NDArray[np.float_] = 1 / DEGREE * np.unwrap(np.angle(ref_fft))
    sample_phase: npt.NDArray[np.float_] = 1 / DEGREE * np.unwrap(np.angle(sample_fft))

    ref_amplitude: npt.NDArray[np.float_] = 1 / len(ref_fft) * np.abs(ref_fft)
    sample_amplitude: npt.NDArray[np.float_] = 1 / len(sample_fft) * np.abs(sample_fft)

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

    return np.array([frequencies, refraction_index, absorption_index]).T[
        range_freq_mask
    ]


def handle_thz(spectrum: Spectrum):
    id = spectrum.id
    if spectrum.raw_file is None:
        update_status(id, "error")
        return {"message": f"Error processing spectrum with id {id}"}

    ref_id = communication.retrieve_reference_spectrum_id(sample_id=spectrum.sample.id)
    if ref_id is not None:
        raw_ref_spectrum = communication.get_spectrum(ref_id)
        if raw_ref_spectrum is None:
            update_status(id, "error")
            return {"message": f"Error retrieving reference spectrum with id {ref_id}"}

        ref_spectrum = Spectrum(**json.loads(raw_ref_spectrum)["spectrum"])
        if (ref_spectrum.raw_file) is None:
            update_status(id, "error")
            return {"message": f"Error getting spectrum file from server"}
        ref_csv = ref_spectrum.to_csv()
        sample_csv = spectrum.to_csv()

        if ref_csv is None or sample_csv is None:
            update_status(id, "error")
            return {"message": f"Error processing spectrum with id {id}"}
        try:
            process_thz(ref_csv, sample_csv, spectrum.sample_thickness)
            update_status(id, "successful")
        except Exception as e:
            logger.error(e)
            update_status(id, "error")
            return {"message": f"Error processing spectrum with id {id}"}

    else:
        try:
            if spectrum.csv_file is None:
                update_status(id, "error")
                return {"message": f"Error coverting spectrum with id {id}"}

            file_patch_response: Response | None = (
                communication.patch_with_processed_file(id, spectrum.csv_file)
            )

            if file_patch_response is None:
                update_status(id, "error")
                return {
                    "message": f"Error uploading processing data to spectrum with id {id}"
                }

            update_status(id, "successful")
            return {"message": f"Done processing for spectrum with id {id}"}

        except Exception as e:
            logger.error(e)
            update_status(id, "error")
