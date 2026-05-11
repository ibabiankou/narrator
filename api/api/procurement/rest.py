from io import BytesIO

from fastapi import APIRouter, UploadFile, BackgroundTasks, HTTPException

from api.models.auth import UserDep
from api.procurement import ProcurementServiceDep

procurement_router = APIRouter(prefix="/procurement", tags=["Procurement API"])


@procurement_router.post("/upload")
def upload(file: UploadFile,
           user: UserDep,
           procurement_service: ProcurementServiceDep,
           background_tasks: BackgroundTasks):
    if file.size > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    procurement_service.upload(file.filename, BytesIO(file.file.read()))
