from fastapi import FastAPI, APIRouter

app = FastAPI()

base_url_router = APIRouter(prefix="/api")


@base_url_router.get("/")
def health():
    return {"status": "ok"}


app.include_router(base_url_router)
