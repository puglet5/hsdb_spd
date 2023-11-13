import logging

from fastapi import APIRouter

from app.config.celery_utils import get_task_info
from app.tasks import processing

logger = logging.getLogger(__name__)

router: APIRouter = APIRouter(
    tags=["Spectrum, Processing"], responses={404: {"description": "Not found"}}
)


@router.post("/processing/{id}", status_code=202)
async def request_processing(
    id: int,
    record_type: str | None = None,
) -> dict:
    """
    Request spectral data processing for record in hsdb with corresponding type and id
    """
    task = processing.process_routine.delay(id)  # type: ignore
    return {
        "message": f"Recieved processing request for {record_type} with id {id}",
        "task": {"id": f"{task}"},
    }


@router.get("/processing/status/{task_id}")
async def get_task_status(task_id: int) -> dict:
    """
    Return the status of the submitted processing job
    """
    return get_task_info(task_id)
