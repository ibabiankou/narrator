import uuid
from datetime import datetime

from fastapi import APIRouter, FastAPI, UploadFile
from pydantic import BaseModel, RootModel
from pydantic.v1 import UUID4

app = FastAPI()

base_url_router = APIRouter(prefix="/api")

class ID(RootModel):
    root: uuid.UUID

class TempFile(BaseModel):
    id: ID
    filename: str
    upload_time: datetime

temp_files = {}

@base_url_router.post("/files/", response_model=TempFile)
def upload_file(file: UploadFile) -> TempFile:
    resp = TempFile(id=uuid.uuid4(), filename=file.filename, upload_time=datetime.utcnow())
    # TODO: Write file to disk and store metadata in DB.
    temp_files[str(resp.id)] = resp
    return resp

app.include_router(base_url_router)
