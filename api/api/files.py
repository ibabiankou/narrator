import logging
import os.path
import uuid
from datetime import datetime, UTC
from typing import Annotated

from fastapi import APIRouter, UploadFile, Request, HTTPException, Response
from fastapi.params import Header

from api import SessionDep
from api.models import db, api
from api.services.files import FilesServiceDep, NotModified

files_router = APIRouter()

local_dir = os.path.dirname("/tmp/narrator/temp_files")
if not os.path.exists(local_dir):
    os.makedirs(local_dir)

LOG = logging.getLogger(__name__)

@files_router.post("/")
def upload_file(file: UploadFile, session: SessionDep) -> api.TempFile:
    file_id = uuid.uuid4()
    upload_time=datetime.now(UTC)

    # Write file to a temp dir
    unique_name = str(file_id) + "_" + file.filename
    temp_file_path = os.path.join(local_dir, unique_name)
    with open(temp_file_path, "wb") as f:
        f.write(file.file.read())

    # store metadata in DB
    session.add(db.TempFile(id=file_id, file_name=file.filename, file_path=temp_file_path, upload_time=upload_time))
    session.commit()

    resp = api.TempFile(id=file_id, filename=file.filename, upload_time=upload_time)

    return resp


@files_router.get("/{key:path}")
def get_file(key: str,
    file_service: FilesServiceDep,
    request: Request,
    if_none_match: Annotated[str | None, Header()] = ""):

    # Handle Range Header: "bytes=0-1023"
    range_header = request.headers.get("Range")
    if range_header:
        range_type, range_val = range_header.split("=")
        start_str, sep, end_str = range_val.partition("-")
        if range_type != "bytes":
            raise HTTPException(status_code=400, detail="Only 'bytes' range type is supported.")
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else -1
        range_request = f"bytes={start}-{end if end != -1 else ''}"
    else:
        range_request = ""

    try:
        LOG.info("Processing range: %s", range_request)
        file_data = file_service._get_object(key, if_none_match, range_request)
    except NotModified:
        return Response(status_code=304)

    if file_data is None:
        raise HTTPException(status_code=404, detail="File not found")

    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=604800",
        "ETag": file_data.etag
    }
    status_code=200
    if file_data.range:
        headers["Content-Range"] = file_data.range
        status_code=206

    return Response(content=file_data.body, status_code=status_code, media_type=file_data.content_type, headers=headers)
