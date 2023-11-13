import logging
import logging.config
import os
import sys

import uvicorn as uvicorn
from fastapi import FastAPI

from app.config.celery_utils import create_celery
from celery.app.task import Task
from app.routers import spectra

Task.__class_getitem__ = classmethod(lambda cls, *args, **kwargs: cls)  # type: ignore[attr-defined]

sys.path.insert(0, os.path.join(os.getcwd(), "app"))

logging.config.fileConfig(fname=r"logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    current_app = FastAPI(
        title="Heritage Science DB Spectral Data Processor",
        version="0.1.0",
    )

    current_app.include_router(spectra.router)
    return current_app


app = create_app()
celery = create_celery()

if __name__ == "__main__":
    uvicorn.run(
        "main:app", port=8000, reload=bool(os.environ.get("HSDB_SDP_DEV", False))
    )
