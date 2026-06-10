import io
import os
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.repository.async_job_repository import AsyncJobRepository
from app.response.job_response import JobStatusResponseDTO, JobResultsResponseDTO, JobUploadResponseDTO
from app.response.standard_response import SuccessResponse
from app.core.exceptions import InvalidFileException, ResourceNotFoundException
from app.worker.tasks import process_transactions_job
from app.main import limiter

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

REQUIRED_COLUMNS = {
    "txn_id", "date", "merchant", "amount",
    "currency", "status", "category", "account_id",
}


@router.post("/upload", response_model=SuccessResponse[JobUploadResponseDTO])
@limiter.limit("10/minute")   # Redis-backed: max 10 uploads per IP per minute
async def upload_csv(
    request: Request,          # required by slowapi for IP extraction
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
):
    # 1. Extension check
    if not file.filename.endswith(".csv"):
        raise InvalidFileException(message="Only CSV files are allowed.")

    # 2. Read file content into memory for validation
    raw_bytes = await file.read()

    # 3. Empty file check
    if len(raw_bytes) == 0:
        raise InvalidFileException(message="Uploaded file is empty.")

    # 4. Max file size check
    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        raise InvalidFileException(
            message=f"File too large. Maximum allowed size is {MAX_FILE_SIZE_MB}MB."
        )

    # 5. Validate parseable CSV with required columns
    try:
        sample_df = pd.read_csv(io.BytesIO(raw_bytes), nrows=0)
    except Exception as e:
        raise InvalidFileException(message=f"Unable to parse CSV file: {str(e)}")

    actual_columns = {c.strip().lower() for c in sample_df.columns}
    missing_columns = {c for c in REQUIRED_COLUMNS if c not in actual_columns}
    if missing_columns:
        raise InvalidFileException(
            message=f"CSV is missing required columns: {sorted(missing_columns)}"
        )

    # 6. Persist file and create job (async DB write)
    repo = AsyncJobRepository(db)
    job = await repo.create_job(filename=file.filename)

    file_path = os.path.join(UPLOAD_DIR, f"{job.id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        buffer.write(raw_bytes)

    process_transactions_job.delay(job.id, file_path)

    return SuccessResponse(
        data=JobUploadResponseDTO(job_id=job.id, status=job.status),
        message="Job created and queued successfully.",
    )


@router.get("/{job_id}/status", response_model=SuccessResponse[JobStatusResponseDTO])
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    repo = AsyncJobRepository(db)
    job = await repo.get_job_by_id(job_id)
    if not job:
        raise ResourceNotFoundException(resource="Job", resource_id=job_id)

    return SuccessResponse(data=JobStatusResponseDTO.model_validate(job))


@router.get("/{job_id}/results", response_model=SuccessResponse[JobResultsResponseDTO])
async def get_job_results(
    job_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    repo = AsyncJobRepository(db)
    job = await repo.get_job_by_id(job_id, load_relations=True)
    if not job:
        raise ResourceNotFoundException(resource="Job", resource_id=job_id)

    result = JobResultsResponseDTO.model_validate(job)
    result.anomalies = [t for t in result.transactions if t.is_anomaly]

    return SuccessResponse(data=result)


@router.get("", response_model=SuccessResponse[List[JobStatusResponseDTO]])
async def list_jobs(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
):
    repo = AsyncJobRepository(db)
    jobs = await repo.list_jobs(status=status)

    data = [JobStatusResponseDTO.model_validate(j) for j in jobs]
    return SuccessResponse(data=data)
