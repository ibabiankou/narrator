from enum import Enum

import logging
import uuid

from fastapi import APIRouter, HTTPException, BackgroundTasks

from api.models.auth import AdminUser
from api.services.books import BookServiceDep

LOG = logging.getLogger(__name__)

processing_router = APIRouter(tags=["Processing API"])


class ProcessingTaskName(str, Enum):
    generate_subtitles = "generate-subtitles"


def check_task_name(task_name):
    if task_name not in ProcessingTaskName:
        raise HTTPException(status_code=400, detail="Invalid task name. Supported tasks: " + ", ".join(ProcessingTaskName) + ".")


@processing_router.post("/{book_id}/{task_name}")
def process_book(book_id: uuid.UUID,
                 task_name: ProcessingTaskName,
                 user: AdminUser,
                 background_tasks: BackgroundTasks,
                 book_service: BookServiceDep):
    check_task_name(task_name)
    book_service.process_book(book_id, task_name, background_tasks)
