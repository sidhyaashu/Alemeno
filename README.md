# AI-Powered Transaction Processing Pipeline

This repository contains the backend implementation for the AI-Powered Transaction Processing Pipeline. It asynchronously processes raw financial transactions using a job queue, cleans the data, detects anomalies, and leverages an LLM to categorize missing transactions and generate a spending narrative.

## Tech Stack
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Job Queue**: Celery + Redis
- **LLM**: Gemini 1.5 Flash (`google-genai` SDK)
- **Containerization**: Docker & Docker Compose
- **Architecture**: Modular, enterprise-grade directory structure with Repository and Service layers.

## Setup Instructions

1. **Clone the repository** (if you haven't already).
2. **Environment Variables**: Rename `.env.example` to `.env` and insert your Gemini API key:
   ```env
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```
3. **Run the Application**: Ensure you have Docker installed and running, then execute:
   ```bash
   docker-compose up --build -d
   ```
   *This single command will spin up the FastAPI server, Celery worker, Redis, and PostgreSQL.*

## API Endpoints

> **Note**: As an architectural best practice, all endpoints are versioned under `/api/v1`. 

### 1. Upload CSV
Accepts a CSV file, enqueues the processing task, and returns the Job ID immediately.
```bash
curl -X POST "http://localhost:8000/api/v1/jobs/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@docs/transactions.csv"
```

### 2. Check Job Status
Returns the status of the job (`pending`, `processing`, `completed`, `failed`).
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/<YOUR_JOB_ID>/status" \
  -H "accept: application/json"
```

### 3. Get Job Results
Returns the full structured output including transactions, anomalies, LLM categories, and the LLM-generated narrative summary.
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/<YOUR_JOB_ID>/results" \
  -H "accept: application/json"
```

### 4. List All Jobs
Lists all processed or pending jobs. Supports filtering by status.
```bash
curl -X GET "http://localhost:8000/api/v1/jobs?status=completed" \
  -H "accept: application/json"
```

## System Design & Data Flow (For Video Presentation)

1. **Request Lifecycle**: The user uploads a CSV to the FastAPI endpoint. FastAPI writes the file to the local disk temporarily, saves a `Job` record to PostgreSQL (status: `pending`), and pushes a task message to Redis.
2. **Asynchronous Processing**: The Celery worker picks up the message from Redis, updates the job status to `processing`, and begins the pipeline.
3. **Pipeline Execution**:
    - **Cleaning**: `pandas` is used to drop exact duplicates, parse dates to ISO 8601, and strip currency symbols.
    - **Anomaly Detection**: Flags transactions > 3x the account's median or USD transactions for domestic merchants.
    - **LLM Classification**: Uncategorized transactions are batched and sent to Gemini.
    - **Narrative**: Aggregated stats are computed and sent to Gemini to generate a narrative and risk level.
4. **Persistence**: The fully processed dataframe is bulk inserted into PostgreSQL. The job status is marked `completed`.

## Scalability & Bottlenecks (For Video Presentation)

If application traffic scales by 100x:
- **Bottleneck 1: Memory Limits**: `pandas.read_csv` loads the entire file into RAM. Huge CSVs will cause the Celery worker to crash with OOM errors.
    - *Solution*: Stream the file using chunking (`pd.read_csv(chunksize=...)`) or switch to Dask/Polars.
- **Bottleneck 2: LLM Rate Limits**: Sending 100,000 transactions at once to Gemini will exceed token limits or rate limits.
    - *Solution*: Process LLM calls in smaller parallel chunks using Celery chord workflows.
- **Bottleneck 3: Database Connections**: Bulk inserts from dozens of scaling workers will overwhelm PostgreSQL connections.
    - *Solution*: Implement a connection pooler like PgBouncer and optimize inserts using PostgreSQL `COPY` instead of ORM bulk saves.
