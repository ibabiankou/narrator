import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, UploadFile
from pydantic import BaseModel

from api.api_models import ID

files_router = APIRouter()


class TempFile(BaseModel):
    id: ID
    filename: str
    upload_time: datetime

temp_files = {}

@files_router.post("/", response_model=TempFile)
def upload_file(file: UploadFile) -> TempFile:
    resp = TempFile(id=uuid.uuid4(), filename=file.filename, upload_time=datetime.now(UTC))
    # TODO: Write file to disk and store metadata in DB.
    temp_files[str(resp.id)] = resp
    return resp
