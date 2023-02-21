import json
import requests
import time

from typing import Union
from typing import List
from celery import shared_task
from app.config.settings import settings


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5},
             name='auth:get_token')
def get_token(self):
    form_data = {
        'email': settings.hsdb_email,
        "password": settings.hsdb_password,
        "grant_type": "password",
        "client_id": settings.hsdb_client_id
    }
    server = requests.post(
        f'{settings.hsdb_url}{"/api/oauth/token"}', data=form_data)

    if server.status_code == 200:
        output = json.loads(server.text)

        settings.access_token = output["access_token"]
        settings.refresh_token = output["refresh_token"]
        settings.token_created_at = output["created_at"]
    else:
        raise Exception("Authentification failed")

def login():
    if not isinstance(settings.token_created_at, int):
        get_token()
    elif time.time()-settings.token_created_at > 7000:
        get_token()


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:list_spectra')
def list_spectra(self):
    login()

    headers = {'Authorization': f'Bearer {settings.access_token}'}
    server = requests.get(
        f'{settings.hsdb_url}{"/api/v1/spectra"}', headers=headers)
    return server.text


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:get_spectrum')
def get_spectrum(self, id: int):
    login()

    headers = {'Authorization': f'Bearer {settings.access_token}'}
    server = requests.get(
        f'{settings.hsdb_url}{"/api/v1/spectra/"}{id}', headers=headers)
    return server.text


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:post_spectrum')
def post_spectrum(sample_id, file_path):
    data = {
        "spectrum[sample_id]": (None, sample_id),
    }

    files = {
        "spectrum[file]": open(file_path, 'rb')
    }

    headers = {
        'Authorization': f'Bearer {settings.access_token}',
    }

    server = requests.post(f'{settings.hsdb_url}{"/api/v1/spectra"}',
                           data=data, headers=headers, files=files)

    return [server.status_code, server.text]


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:patch_spectrum')
def patch_with_processed_file(self, id: int, file):
    files = {
        "spectrum[processed_file]": file
    }

    headers = {
        'Authorization': f'Bearer {settings.access_token}',
    }

    request = requests.patch(
        f'{settings.hsdb_url}/api/v1/spectra/{id}', headers=headers, files=files)

    return [request.status_code, request.text]


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:update_status')
def update_status(self, id: int, status: str):
    data = {
        "spectrum[status]": status,
    }

    headers = {
        'Authorization': f'Bearer {settings.access_token}',
    }

    server = requests.patch(f'{settings.hsdb_url}{"/api/v1/spectra/"}{id}',
                            data=data, headers=headers)

    return [server.status_code, server.text]


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='notiify')
def notify(id: int, record: Union[str, None] = None, status="", message=""):
    return f"id {id}, record {record}, {message}"
