from io import BytesIO
import json
import logging
from typing import TypeAlias, TypedDict
import numpy as np
import numpy.typing as npt

from celery import shared_task
import numpy as np
import pandas as pd
from requests import Response

from app.config.settings import settings

from ..tasks import communication
from ..tools.converters import (
    construct_metadata,
    convert_to_csv,
    download_file,
    find_peaks,
    validate_json,
)

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


class Spectrum(TypedDict):
    file_url: str
    filename: str
    id: int
    sample: dict[str, int]
    format: str
    status: str
    category: str
    range: str
    metadata: str | dict | None
    sample_thickness: float


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 0},
    name="spectra:process_spectrum",
)
def process_spectrum(self, id: int) -> dict[str, str]:
    """
    Process spectrum with corresponding id
    """
    if (raw_spectrum := communication.get_spectrum(id)) is None:
        communication.update_status(id, "error")
        return {"message": f"Error retrieving spectrum with {id}"}
    spectrum: Spectrum = json.loads(raw_spectrum)["spectrum"]

    file_url: URL = f'{settings.hsdb_url}{spectrum["file_url"]}'
    filename: str = spectrum["filename"]

    communication.update_status(id, "ongoing")

    if (file := download_file(file_url)) is None:
        communication.update_status(id, "error")
        return {"message": f"Error getting spectrum file from server"}

    if spectrum["category"] == "thz":
        handle_thz(id, spectrum, file)
        return {"message": f"Done processing for thz spectrum with id {id}"}

    if (processed_file := convert_to_csv(file, filename)) is None:
        communication.update_status(id, "error")
        return {"message": f"Error coverting spectrum with id {id}"}
    peak_data = find_peaks(processed_file)

    processed_file.seek(0)

    file_patch_response: Response | None = communication.patch_with_processed_file(
        id, processed_file
    )

    metadata_patch_response: Response | None = None
    if validate_json(spectrum["metadata"]) and peak_data is not None:
        if (
            metadata := construct_metadata(spectrum["metadata"], peak_data)
        ) is not None:
            metadata_patch_response = communication.update_metadata(id, metadata)

    processed_file.close()

    if metadata_patch_response is None or file_patch_response is None:
        communication.update_status(id, "error")
        return {"message": f"Error uploading processing data to spectrum with id {id}"}

    communication.update_status(id, "successful")

    return {"message": f"Done processing for spectrum with id {id}"}


def process_thz(ref_csv: BytesIO, sample_csv: BytesIO, sample_thickness: float):
    """
    Extracts refraction and absorption index from THz TDS data.

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


def handle_thz(id: int, spectrum: Spectrum, sample_file: BytesIO):
    ref_id = communication.retrieve_reference_spectrum_id(
        sample_id=spectrum["sample"]["id"]
    )
    if ref_id is not None:
        raw_ref_spectrum = communication.get_spectrum(ref_id)
        if raw_ref_spectrum is not None:
            ref_spectrum: Spectrum = json.loads(raw_ref_spectrum)["spectrum"]
            ref_url = f'{settings.hsdb_url}{ref_spectrum["file_url"]}'
            if (ref_file := download_file(ref_url)) is None:
                communication.update_status(id, "error")
                return {"message": f"Error getting spectrum file from server"}
            ref_csv = convert_to_csv(ref_file, ref_spectrum["filename"])
            sample_csv = convert_to_csv(sample_file, spectrum["filename"])
            sample_thickness = float(spectrum["sample_thickness"])

            if ref_csv is not None and sample_csv is not None:
                try:
                    process_thz(ref_csv, sample_csv, sample_thickness)
                    communication.update_status(id, "successful")
                except Exception as e:
                    logger.error(e)
                    communication.update_status(id, "error")
            else:
                communication.update_status(id, "error")
        else:
            communication.update_status(id, "error")
    else:
        try:
            if (
                processed_file := convert_to_csv(sample_file, spectrum["filename"])
            ) is None:
                communication.update_status(id, "error")
                return {"message": f"Error coverting spectrum with id {id}"}
            processed_file.seek(0)

            file_patch_response: Response | None = (
                communication.patch_with_processed_file(id, processed_file)
            )

            if file_patch_response is None:
                communication.update_status(id, "error")
                return {
                    "message": f"Error uploading processing data to spectrum with id {id}"
                }

            communication.update_status(id, "successful")
            return {"message": f"Done processing for spectrum with id {id}"}

        except Exception as e:
            logger.error(e)
            communication.update_status(id, "error")
