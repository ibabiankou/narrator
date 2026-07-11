import uuid
from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import NoResultFound

from api.models.auth import AdminUser
from api.services.books import BookServiceDep
from api.services.experimental import identify_book
from api.utils.imgproxy import ImgProxy

experimental_router = APIRouter(tags=["Experimental API"])


@experimental_router.get("/{book_id}/llm_metadata")
def llm_metadata(book_id: uuid.UUID,
                 book_service: BookServiceDep,
                 user: AdminUser):
    try:
        book = book_service.get_book(book_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")

    # first_pages = book_service.get_text(book, 0, 10, False)
    # TODO: Use other than body-matter parts of the epub book.
    first_pages = ""
    book_metadata = identify_book(first_pages)

    return book_metadata


@experimental_router.get("/imgproxy-url")
def generate_and_sign_imgproxy_url(processing_options: str,
                                   source_image: str,
                                   seo_file_name: str,
                                   user: AdminUser) -> str:
    img_proxy = ImgProxy()
    return img_proxy.build_url(source_image, seo_file_name, processing_options)
