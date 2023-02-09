import uvicorn as uvicorn
import sys
import os

from fastapi import FastAPI
from app.config.celery_utils import create_celery
from app.routers import processing

sys.path.insert(0, os.path.join(os.getcwd(), 'app'))


def create_app() -> FastAPI:
    current_app = FastAPI(title="Heritage Science DB Spectral Data Processor",
                          version="0.1.0", )

    current_app.include_router(processing.router)
    current_app.celery_app = create_celery()
    return current_app


app = create_app()
celery = app.celery_app

if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)
