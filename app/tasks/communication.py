import json
import requests
import time
import io
import logging

from typing import Union, List
from requests import Response
from celery import shared_task
from app.config.settings import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5},
             name='auth:get_token')
def get_token(self) -> None:
    form_data = {
        'email': settings.hsdb_email,
        "password": settings.hsdb_password,
        "grant_type": "password",
        "client_id": settings.hsdb_client_id
    }
    try:
        response = requests.post(
            f'{settings.hsdb_url}{"/api/oauth/token"}', data=form_data)
    except Exception as e:
        logger.error(e)
        return None

    if response.status_code == 200:
        token_params: dict = json.loads(response.text)

        settings.access_token = token_params["access_token"]
        settings.refresh_token = token_params["refresh_token"]
        settings.token_created_at = token_params["created_at"]
    else:
        raise Exception("Authentification failed")


def login() -> None:
    token_exists: bool = settings.token_created_at is not None
    if settings.token_created_at is not None:
        token_expired: bool = True if int(time.time(
        ))-settings.token_created_at > 7200 else False

        if token_expired | (not token_exists):
            get_token()
    else:
        get_token()


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:list_spectra')
def list_spectra(self) -> str | None:
    login()

    try:
        headers = {'Authorization': f'Bearer {settings.access_token}'}
        response = requests.get(
            f'{settings.hsdb_url}{"/api/v1/spectra"}', headers=headers)
        return response.text
    except Exception as e:
        logger.error(e)
        return None


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:get_spectrum')
def get_spectrum(self, id: int) -> str | None:
    login()

    try:
        headers = {
            'Authorization': f'Bearer {settings.access_token}'
        }

        response = requests.get(
            f'{settings.hsdb_url}{"/api/v1/spectra/"}{id}', headers=headers)
        return response.text
    except Exception as e:
        logger.error(e)
        return None


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:post_spectrum')
def post_spectrum(sample_id, file_path) -> Response | None:
    data = {
        "spectrum[sample_id]": (None, sample_id),
    }

    files = {
        "spectrum[file]": open(file_path, 'rb')
    }

    headers = {
        'Authorization': f'Bearer {settings.access_token}',
    }
    try:
        response = requests.post(f'{settings.hsdb_url}{"/api/v1/spectra"}',
                                 data=data, headers=headers, files=files)
        return response
    except Exception as e:
        logger.error(e)
        return None


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:patch_spectrum')
def patch_with_processed_file(self, id: int, file: io.BytesIO) -> Response | None:
    files = {
        "spectrum[processed_file]": file
    }

    headers = {
        'Authorization': f'Bearer {settings.access_token}',
    }
    try:
        response = requests.patch(
            f'{settings.hsdb_url}/api/v1/spectra/{id}', headers=headers, files=files)
        return response
    except Exception as e:
        logger.error(e)
        return None


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:update_status')
def update_status(self, id: int, status: str) -> Response | None:
    data = {
        "spectrum[status]": status,
    }

    headers = {
        'Authorization': f'Bearer {settings.access_token}',
    }
    try:
        response = requests.patch(f'{settings.hsdb_url}{"/api/v1/spectra/"}{id}',
                                  data=data, headers=headers)
        return response
    except Exception as e:
        logger.error(e)
        return None


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='spectra:update_metadata')
def update_metadata(self, id: int, metadata: dict) -> Response | None:
    data = {
        "spectrum[metadata]": json.dumps(metadata),
    }

    headers = {
        'Authorization': f'Bearer {settings.access_token}',
    }
    try:
        response = requests.patch(f'{settings.hsdb_url}{"/api/v1/spectra/"}{id}',
                                  data=data, headers=headers)
        return response
    except Exception as e:
        logger.error(e)
        return None


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 0},
             name='notify')
def notify(id: int, record: Union[str, None] = None, status="", message="") -> str:
    return f"id {id}, record {record}, {message}"
