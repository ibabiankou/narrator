from fastapi import APIRouter, FastAPI

app = FastAPI()

base_url_router = APIRouter(prefix="/api")

@base_url_router.get("/")
def read_root():
    return {"Hello": "World"}

app.include_router(base_url_router)
