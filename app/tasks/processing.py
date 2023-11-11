from io import BytesIO
import json
import logging
from typing import TypeAlias, TypedDict

from celery import shared_task
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


def process_thz(files: tuple[BytesIO, ...]):
    """
    Extracts refraction and absorption index from THz TDS data.

    First file in a `files` tuple must be a reference spectrum.
    """
    ...


def handle_thz(id: int, spectrum: Spectrum, sample_file: BytesIO):
    ref_id = communication.retrieve_reference_spectrum_id(
        sample_id=spectrum["sample"]["id"]
    )
    ref_url = f'{settings.hsdb_url}{json.loads(communication.get_spectrum(ref_id))["spectrum"]["file_url"]}'
    if (ref_file := download_file(ref_url)) is None:
        communication.update_status(id, "error")
        return {"message": f"Error getting spectrum file from server"}
    process_thz((ref_file, sample_file))
    communication.update_status(id, "successful")
