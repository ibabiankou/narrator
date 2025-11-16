import os.path
import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, UploadFile
from pydantic import BaseModel

from api import SessionDep
from api.models import models

files_router = APIRouter()

local_dir = os.path.dirname("/tmp/narrator/temp_files")
if not os.path.exists(local_dir):
    os.makedirs(local_dir)

class TempFile(BaseModel):
    id: uuid.UUID
    filename: str
    upload_time: datetime

@files_router.post("/", response_model=TempFile)
def upload_file(file: UploadFile, session: SessionDep) -> TempFile:
    file_id = uuid.uuid4()
    upload_time=datetime.now(UTC)

    # Write file to a temp dir
    unique_name = str(file_id) + "_" + file.filename
    temp_file_path = os.path.join(local_dir, unique_name)
    with open(temp_file_path, "wb") as f:
        f.write(file.file.read())

    # store metadata in DB
    session.add(models.TempFile(id=file_id, file_name=file.filename, file_path=temp_file_path, upload_time=upload_time))
    session.commit()

    resp = TempFile(id=file_id, filename=file.filename, upload_time=upload_time)

    return resp
