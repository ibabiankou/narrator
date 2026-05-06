import logging
import os.path
from typing import Annotated

from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.params import Header

from api.services.files import FilesServiceDep, NotModified

files_router = APIRouter(tags=["Files API"])

local_dir = os.path.dirname("/tmp/narrator/temp_files")
if not os.path.exists(local_dir):
    os.makedirs(local_dir)

LOG = logging.getLogger(__name__)


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

    if range_request:
        LOG.info("Processing range: %s", range_request)
    file_data = file_service._get_object(key, if_none_match, range_request)

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
