from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Depends
from starlette.middleware.gzip import GZipMiddleware

from api.books import books_router
from api.files import files_router
from api.services.files import FilesService

app = FastAPI()
origins = [
    "http://localhost",
    "http://localhost:4200",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware)

base_url_router = APIRouter(prefix="/api")

@base_url_router.get("/")
def health():
    return {"status": "ok"}


base_url_router.include_router(files_router, prefix="/files")
base_url_router.include_router(books_router, prefix="/books")
app.include_router(base_url_router)
