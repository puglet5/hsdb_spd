import uvicorn as uvicorn
from fastapi import FastAPI

from config.celery_utils import create_celery


def create_app() -> FastAPI:
    current_app = FastAPI(title="Heritage Science DB Spectral Data Processor",
                          version="0.1.0", )

    current_app.celery_app = create_celery()
    current_app.include_router(universities.router)
    return current_app


app = create_app()
celery = app.celery_app


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)
