import pandas as pd
import numpy as np
import io
import json
import requests
import csv
import codecs
from app.config.settings import settings

from ..tasks import communication

from typing import Union
from typing import List
from celery import shared_task


def download_file(url):
    """
    Downloads file from given url and return it as memory buffer
    """
    try:
        response = requests.get(url)
        file = io.BytesIO(response.content)
        return file
    except Exception as e:
        return e


def convert_dpt(file, filename):
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
def process_spectrum(self, id: int):
    hsdb_url = settings.hsdb_url
    spectrum = json.loads(communication.get_spectrum(id))["spectrum"]
    file_url = f'{hsdb_url}{spectrum["file_url"]}'
    filename = spectrum["filename"]

    communication.update_status(id, "ongoing")

    file = download_file(file_url)
    processed_file = convert_dpt(file, filename)

    communication.patch_with_processed_file(id, processed_file)

    processed_file.flush()
    processed_file.seek(0)

    communication.update_status(id, "successful")

    return {"message": f"successfully processed spectrum with id {id}"}
