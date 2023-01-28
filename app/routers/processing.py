import app.tasks.tasks

from fastapi import APIRouter
from typing import Union
from app.config.celery_utils import get_task_info

router = APIRouter(prefix='/processing',
                   tags=['Spectrum, Processing'], responses={404: {"description": "Not found"}})


@router.post("/{id}", status_code=202)
def request_processing(id, type: Union[str, None] = None,) -> dict:
    """
    Request spectral data processing for record in hsdb with corresponding type and id
    """
    return {id}


@router.get("/status/{task_id}")
async def get_task_status(task_id: str) -> dict:
    """
    Return the status of the submitted Task
    """
    return get_task_info(task_id)
