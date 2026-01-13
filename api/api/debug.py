import uuid
from typing import Optional, Annotated

from fastapi import APIRouter, HTTPException
from fastapi.params import Query
from starlette.responses import Response

from api import SessionDep
from api.models import db
from api.services.books import BookServiceDep

debug_router = APIRouter()


@debug_router.get("/{book_id}/text")
def text(book_id: uuid.UUID,
             session: SessionDep,
             book_service: BookServiceDep,
             first_page: Annotated[Optional[int], Query()] = None,
             last_page: Annotated[Optional[int], Query()] = None,
             raw: bool = False):
    book = session.get(db.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    return Response(content=book_service.get_text(book, first_page, last_page, raw),
                    media_type="text/plain")

@debug_router.get("/{book_id}/paragraphs")
def paragraphs(book_id: uuid.UUID,
             session: SessionDep,
             book_service: BookServiceDep,
             first_page: Annotated[Optional[int], Query()] = None,
             last_page: Annotated[Optional[int], Query()] = None):
    book = session.get(db.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    return Response(content=book_service.get_paragraphs(book, first_page, last_page),
                    media_type="text/plain")
