import io
import json
import requests
import csv
import codecs
import numpy as np
import pandas as pd
from findpeaks import findpeaks

from app.config.settings import settings
from celery import shared_task
from ..tasks import communication

URL = str


def download_file(url: URL) -> io.BytesIO:
    """
    Download file from given url and return it as an in-memory buffer
    """
    try:
        response = requests.get(url)
        file: io.BytesIO = io.BytesIO(response.content)
        file.seek(0)
        return file
    except Exception as e:
        return e  # type: ignore


def find_peaks(file: io.BytesIO) -> np.ndarray:
    data = np.loadtxt(file, delimiter=",")[:, 1]
    data = data / np.max(data)
    fp = findpeaks(method='topology', lookahead=2, denoise="bilateral")
    result = fp.fit(data)
    df: pd.DataFrame = result["df"]  # type: ignore

    filtered_pos = df.query('peak == True & rank != 0 & rank < 40 & y >= 0.05')[
        "x"].to_numpy()
    return filtered_pos


def convert_dpt(file: io.BytesIO, filename: str) -> io.BytesIO:
    """
    Convert FTIR .1.dpt and .0.dpt files to .csv
    """
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


def construct_metadata(init: dict, peak_data: np.ndarray) -> dict:
    peak_metadata = {"peaks": [{"position": str(i)} for i in peak_data]}
    return {**init, **peak_metadata}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:process_spectrum')
def process_spectrum(self, id: int) -> dict:
    """
    Process passed spectrum based on its filetype

    Filetype is defined in spectrum["format"]. Supported filetypes: .dpt
    """
    hsdb_url: URL = settings.hsdb_url
    spectrum: dict = json.loads(communication.get_spectrum(id))["spectrum"]
    file_url: URL = f'{hsdb_url}{spectrum["file_url"]}'
    filename: str = spectrum["filename"]

    file: io.BytesIO = download_file(file_url)
    communication.update_status(id, "ongoing")

    if spectrum["format"] == "dpt":
        try:
            processed_file: io.BytesIO = convert_dpt(file, filename)
            peak_data: np.ndarray = find_peaks(processed_file)
        except Exception as e:
            communication.update_status(id, "error")
            return {"message": f"error coverting spectrum with id {id} ({str(e)})"}
    else:
        communication.update_status(id, "error")
        return {"message": f"unsupported filetype for spectrum with id {id}"}

    processed_file.seek(0)
    communication.patch_with_processed_file(id, processed_file)
    communication.update_metadata(
        id, construct_metadata(spectrum["metadata"], peak_data))

    processed_file.flush()
    processed_file.seek(0)

    communication.update_status(id, "successful")

    return {"message": peak_data}
