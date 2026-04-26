import uuid
from typing import Optional, Annotated

from fastapi import APIRouter, HTTPException
from fastapi.params import Query
from sqlalchemy.exc import NoResultFound
from starlette.responses import Response

from api.models.auth import AdminUser
from api.services.books import BookServiceDep
from api.services.experimental import identify_book

experimental_router = APIRouter(tags=["Experimental API"])


@experimental_router.get("/{book_id}/text")
def text(book_id: uuid.UUID,
         book_service: BookServiceDep,
         user: AdminUser,
         first_page: Annotated[Optional[int], Query()] = None,
         last_page: Annotated[Optional[int], Query()] = None,
         raw: bool = False):
    try:
        book = book_service.get_book(book_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")

    return Response(content=book_service.get_text(book, first_page, last_page, raw),
                    media_type="text/plain")


@experimental_router.get("/{book_id}/paragraphs")
def paragraphs(book_id: uuid.UUID,
               book_service: BookServiceDep,
               user: AdminUser,
               first_page: Annotated[Optional[int], Query()] = None,
               last_page: Annotated[Optional[int], Query()] = None):
    try:
        book = book_service.get_book(book_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")

    return Response(content=book_service.get_paragraphs(book, first_page, last_page),
                    media_type="text/plain")


@experimental_router.get("/{book_id}/llm_metadata")
def llm_metadata(book_id: uuid.UUID,
                 book_service: BookServiceDep,
                 user: AdminUser):
    try:
        book = book_service.get_book(book_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")

    first_pages = book_service.get_text(book, 0, 10, False)
    book_metadata = identify_book(first_pages)

    return book_metadata
