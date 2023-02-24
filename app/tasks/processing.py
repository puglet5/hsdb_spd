import json
import logging

from typing import TypedDict
from requests import Response
from collections.abc import Callable

from app.config.settings import settings
from celery import shared_task
from ..tasks import communication
from ..tools.converters import *

logger = logging.getLogger(__name__)

URL = str


class Spectrum(TypedDict):
    file_url: str
    filename: str
    id: int
    sample: dict[int, str]
    format: str
    status: str
    category: str
    range: str
    metadata: str | dict | None


dispatch: dict[str, Callable] = {
    "dpt": convert_dpt,
    "csv": validate_csv,
    "dat": convert_dat
}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:process_spectrum')
def process_spectrum(self, id: int) -> dict[str, str]:
    """
    Process passed spectrum based on its filetype

    Filetype is defined in spectrum["format"]. Supported filetypes: .dpt, .dat, .csv
    """
    if (raw_spectrum := communication.get_spectrum(id)) is None:
        communication.update_status(id, "error")
        return {"message": f"Error retrieving spectrum with {id}"}
    spectrum: Spectrum = json.loads(raw_spectrum)["spectrum"]

    file_url: URL = f'{settings.hsdb_url}{spectrum["file_url"]}'
    filename: str = spectrum["filename"]
    filetype: str = spectrum["format"]

    communication.update_status(id, "ongoing")

    if (file := download_file(file_url)) is None:
        communication.update_status(id, "error")
        return {"message": f"Error getting spectrum file from server"}

    if filetype not in dispatch:
        communication.update_status(id, "error")
        return {"message": f"Unsupported filetype for spectrum with id {id}"}
    if (processed_file := dispatch[filetype](file, filename)) is None:
        communication.update_status(id, "error")
        return {"message": f"Error coverting spectrum with id {id}"}
    peak_data = find_peaks(processed_file)

    processed_file.seek(0)

    file_patch_response: Response | None = \
        communication.patch_with_processed_file(
            id, processed_file)

    metadata_patch_response: Response | None = None
    if validate_json(spectrum["metadata"]) and peak_data is not None:
        if (metadata := construct_metadata(spectrum["metadata"], peak_data)) is not None:
            metadata_patch_response = communication.update_metadata(
                id, metadata)

    processed_file.close()

    if metadata_patch_response is None \
            or file_patch_response is None:
        communication.update_status(id, "error")
        return {"message": f"Error uploading processing data to spectrum with id {id}"}

    communication.update_status(id, "successful")

    return {"message": f"Done processing for spectrum with id {id}"}
