import responses
from fastapi.testclient import TestClient

from .config.settings import settings
from .main import app
from .tasks import communication as db
from .tasks import processing as proc
from .tasks.processing import process_routine

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 404


def test_process_spectrum():
    response = client.post("/processing/1")
    assert response.status_code == 202


@responses.activate
def test_celery_processing():
    responses.add(
        responses.POST,
        f'{settings.db_url}{"/api/oauth/token"}',
        status=401,
    )
    resp = proc.process_spectrum(1)

    assert resp["status"] == "error"
