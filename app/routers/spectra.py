from fastapi import APIRouter

import tasks.tasks
from config.celery_utils import get_task_info

router = APIRouter(prefix='/spectra',
                   tags=['Spectrum'], responses={404: {"description": "Not found"}})


@router.post("/{id}", status_code=202)
def request_processing(id) -> dict:
    """
    Request spectral data processing for spectrum record in hsdb with corresponding id
    """
    return {id}


@router.get("/status/{task_id}")
async def get_task_status(task_id: str) -> dict:
    """
    Return the status of the submitted Task
    """
    return get_task_info(task_id)
