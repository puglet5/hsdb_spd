import io
import json
import requests
import csv
import codecs
import numpy as np
import numpy.typing as npt
import pandas as pd
import logging

from findpeaks import findpeaks
from typing import TypedDict
from requests import Response

from app.config.settings import settings
from celery import shared_task
from ..tasks import communication

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


def validate_json(json_data) -> bool:
    if isinstance(json_data, dict):
        return True
    try:
        json.loads(str(json_data))
    except (ValueError, TypeError) as err:
        return False
    return True


def download_file(url: URL) -> io.BytesIO | None:
    """
    Download file from given url and return it as an in-memory buffer
    """
    try:
        response = requests.get(url)
    except Exception as e:
        logger.error(e)
        return None
    file: io.BytesIO = io.BytesIO(response.content)
    file.seek(0)
    return file


def find_peaks(file: io.BytesIO) -> npt.NDArray | None:
    data = np.loadtxt(file, delimiter=",")[:, 1]
    data = data / np.max(data)
    fp = findpeaks(method='topology', lookahead=2, denoise="bilateral")
    result = fp.fit(data)
    if result:
        df: pd.DataFrame = result["df"]
    else:
        return None

    filtered_pos: npt.NDArray = df.query('peak == True & rank != 0 & rank <= 40 & y >= 0.03')[
        "x"].to_numpy()
    return filtered_pos


def convert_dpt(file: io.BytesIO, filename: str) -> io.BytesIO | None:
    """
    Convert FTIR .1.dpt and .0.dpt files to .csv
    """
    try:
        csv_data = csv.reader(codecs.iterdecode(file, 'utf-8'))
        file.flush()
        file.seek(0)

        sio: io.StringIO = io.StringIO()

        writer = csv.writer(sio, dialect='excel', delimiter=',')
        for row in csv_data:
            writer.writerow(row)

        sio.seek(0)
        bio = io.BytesIO(sio.read().encode('utf8'))

        sio.flush()
        sio.seek(0)

        bio.name = f'{filename.rsplit(".", 2)[0]}.csv'
        bio.seek(0)

        return bio
    except Exception as e:
        logger.error(e)
        return None


def construct_metadata(init, peak_data: npt.NDArray) -> dict | None:
    """
    Construct JSON object from existing spectrum metadata and peak metadata from processing
    """
    peak_metadata = {"peaks": [{"position": str(i)} for i in peak_data]}
    if isinstance(init, str):
        return {**json.loads(init), **peak_metadata}
    elif isinstance(init, dict):
        return {**init, **peak_metadata}
    else:
        return None


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:process_spectrum')
def process_spectrum(self, id: int) -> dict[str, str]:
    """
    Process passed spectrum based on its filetype

    Filetype is defined in spectrum["format"]. Supported filetypes: .dpt
    """
    hsdb_url: URL = settings.hsdb_url
    spectrum: Spectrum = json.loads(communication.get_spectrum(id))["spectrum"]
    file_url: URL = f'{hsdb_url}{spectrum["file_url"]}'
    filename: str = spectrum["filename"]

    communication.update_status(id, "ongoing")

    file = download_file(file_url)
    if file is None:
        communication.update_status(id, "error")
        return {"message": f"Error getting spectrum file from server"}

    if spectrum["format"] == "dpt":
        processed_file = convert_dpt(file, filename)
        if processed_file is not None:
            peak_data = find_peaks(processed_file)
        else:
            communication.update_status(id, "error")
            return {"message": f"Error coverting spectrum with id {id}"}
    else:
        communication.update_status(id, "error")
        return {"message": f"Unsupported filetype for spectrum with id {id}"}

    processed_file.seek(0)

    file_patch_response: Response = communication.patch_with_processed_file(
        id, processed_file)

    metadata_patch_response: Response | None = None
    if validate_json(spectrum["metadata"]) and peak_data is not None:
        metadata = construct_metadata(spectrum["metadata"], peak_data)
        if metadata is not None:
            metadata_patch_response = communication.update_metadata(
                id, metadata)

    processed_file.flush()
    processed_file.seek(0)

    if metadata_patch_response is not None and file_patch_response is not None:
        communication.update_status(id, "successful")
    else:
        communication.update_status(id, "error")

    return {"message": f"Done processing spectrum with id {id}"}
