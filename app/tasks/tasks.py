import dotenv
import os
import json
import requests
import time

from typing import List
from celery import shared_task

dotenv_file = dotenv.find_dotenv()
hsdb_url = os.getenv("HDSB_URL")


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5},
             name='auth:get_token')
def get_token(self):
    dotenv.load_dotenv(dotenv_path=dotenv_file)

    form_data = {
        'email': os.getenv("HDSB_CLIENT_ID"),
        "password": os.getenv("HDSB_PASSWORD"),
        "grant_type": "password",
        "client_id": os.getenv("HDSB_CLIENT_ID")
    }
    server = requests.post(
        f'{hsdb_url}{"/api/oauth/token"}', data=form_data)
    output = json.loads(server.text)

    dotenv.set_key(dotenv_file, "ACCESS_TOKEN", output["access_token"])
    dotenv.set_key(dotenv_file, "REFRESH_TOKEN",
                   output["refresh_token"])
    dotenv.set_key(dotenv_file, "TOKEN_CREATED_AT",
                   str(output["created_at"]))

    return output["access_token"]


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:list_spectra')
def list_spectra(self):
    headers = {'Authorization': f'Bearer {os.getenv("ACCESS_TOKEN")}'}
    server = requests.get(f'{hsdb_url}{"/api/v1/samples"}', headers=headers)
    return server.text


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:get_spectrum')
def get_spectrum(self, id: str):
    headers = {'Authorization': f'Bearer {os.getenv("ACCESS_TOKEN")}'}
    server = requests.get(
        f'{hsdb_url}{"/api/v1/samples/"}{id}', headers=headers)
    return server.text
