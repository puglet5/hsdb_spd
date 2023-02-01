from app.tasks import communication, tools
import json

from fastapi import APIRouter
from typing import Union
from app.config.celery_utils import get_task_info

router = APIRouter(prefix='/processing',
                   tags=['Spectrum, Processing'], responses={404: {"description": "Not found"}})


@router.post("/{id}", status_code=202)
async def request_processing(id: int, record_type: Union[str, None] = None,) -> dict:
    """
    Request spectral data processing for record in hsdb with corresponding type and id
    """
    tools.process_spectrum.apply_async(args=[id])
    return {"message": f"Recieved processing request for {record_type} with id {id}"}


@router.get("/status/{task_id}")
async def get_task_status(task_id: int) -> dict:
    """
    Return the status of the submitted processing job
    """
    return get_task_info(task_id)
