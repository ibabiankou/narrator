import logging
import uuid

from fastapi import APIRouter, HTTPException, BackgroundTasks

from api import SessionDep
from api.models import db
from api.models.auth import AdminUser
from api.services.books import BookServiceDep

LOG = logging.getLogger(__name__)

processing_router = APIRouter(tags=["Processing API"])

tasks = ["split-pages", "extract-text", "extract-images"]


def check_task_name(task_name):
    if task_name not in tasks:
        raise HTTPException(status_code=400, detail="Invalid task name. Supported tasks: " + ", ".join(tasks) + ".")


@processing_router.post("/{book_id}/{task_name}")
def process_book(book_id: uuid.UUID,
                 task_name: str,
                 user: AdminUser,
                 session: SessionDep,
                 background_tasks: BackgroundTasks,
                 book_service: BookServiceDep):
    book = session.get(db.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    check_task_name(task_name)

    if task_name == "split-pages":
        background_tasks.add_task(book_service.split_pages, book.id, book.file_name)

    if task_name == "extract-text":
        background_tasks.add_task(book_service.extract_text, book.id, book.file_name)

    if task_name == "extract-images":
        background_tasks.add_task(book_service.extract_and_store_images, book.id, book.file_name)
