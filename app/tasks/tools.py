import io
import json
import requests
import csv
import codecs

from app.config.settings import settings
from celery import shared_task
from ..tasks import communication

URL = str


def download_file(url: URL) -> io.BytesIO:
    """
    Downloads file from given url and return it as memory buffer
    """
    try:
        response = requests.get(url)
        file = io.BytesIO(response.content)
        return file
    except Exception as e:
        return e  # type: ignore


def convert_dpt(file: io.BytesIO, filename: str) -> io.BytesIO:
    """
    Converts FTIR .1.dpt and .0.dpt files to .csv
    """
    csv_data = csv.reader(codecs.iterdecode(file, 'utf-8'))
    file.flush()
    file.seek(0)

    sio = io.StringIO()

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


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:process_spectrum')
def process_spectrum(self, id: int) -> dict:
    """
    Processes passed spectrum based on its filetype
    Filetype is defined in spectrum["format"]
    """
    hsdb_url: URL = settings.hsdb_url
    spectrum: dict = json.loads(communication.get_spectrum(id))["spectrum"]
    file_url: URL = f'{hsdb_url}{spectrum["file_url"]}'
    filename: str = spectrum["filename"]

    communication.update_status(id, "ongoing")

    file = download_file(file_url)
    if spectrum["format"] == "dpt":
        try:
            processed_file = convert_dpt(file, filename)
        except Exception as e:
            communication.update_status(id, "error")
            return {"message": f"error coverting spectrum with id {id} ({str(e)})"}
    else:
        communication.update_status(id, "error")
        return {"message": f"unsupported filetype for spectrum with id {id}"}

    communication.patch_with_processed_file(id, processed_file)

    processed_file.flush()
    processed_file.seek(0)

    communication.update_status(id, "successful")

    return {"message": f"successfully processed spectrum with id {id}"}
