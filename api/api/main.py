from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.books import books_router
from api.files import files_router

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

base_url_router = APIRouter(prefix="/api")

@base_url_router.get("/")
def health():
    return {"status": "ok"}

base_url_router.include_router(files_router, prefix="/files")
base_url_router.include_router(books_router, prefix="/books")
app.include_router(base_url_router)
