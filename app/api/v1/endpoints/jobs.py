import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repository.job_repository import JobRepository
from app.response.job_response import JobStatusResponseDTO, JobResultsResponseDTO, JobUploadResponseDTO
from app.response.standard_response import SuccessResponse
from app.core.exceptions import InvalidFileException, ResourceNotFoundException
from app.worker.tasks import process_transactions_job

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=SuccessResponse[JobUploadResponseDTO])
def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise InvalidFileException(message="Only CSV files are allowed.")
    
    repo = JobRepository(db)
    job = repo.create_job(filename=file.filename)
    
    file_path = os.path.join(UPLOAD_DIR, f"{job.id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    process_transactions_job.delay(job.id, file_path)
    
    return SuccessResponse(
        data=JobUploadResponseDTO(job_id=job.id, status=job.status),
        message="Job created and queued successfully."
    )

@router.get("/{job_id}/status", response_model=SuccessResponse[JobStatusResponseDTO])
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    job = repo.get_job_by_id(job_id)
    if not job:
        raise ResourceNotFoundException(resource="Job", resource_id=job_id)
        
    return SuccessResponse(data=JobStatusResponseDTO.model_validate(job))

@router.get("/{job_id}/results", response_model=SuccessResponse[JobResultsResponseDTO])
def get_job_results(job_id: str, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    job = repo.get_job_by_id(job_id)
    if not job:
        raise ResourceNotFoundException(resource="Job", resource_id=job_id)
        
    return SuccessResponse(data=JobResultsResponseDTO.model_validate(job))

@router.get("", response_model=SuccessResponse[List[JobStatusResponseDTO]])
def list_jobs(status: Optional[str] = None, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    jobs = repo.list_jobs(status=status)
    
    data = [JobStatusResponseDTO.model_validate(j) for j in jobs]
    return SuccessResponse(data=data)
