# AI-Powered Transaction Processing Pipeline

> **Backend + DevOps Intern Assignment** — Asynchronous CSV ingestion, LLM-powered classification, anomaly detection, and structured reporting via a production-grade REST API.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Processing Pipeline](#processing-pipeline)
- [Scalability & Bottlenecks](#scalability--bottlenecks)
- [Running Tests](#running-tests)

---

## Overview

This service accepts a dirty financial transactions CSV, processes it asynchronously through a job queue, and returns:

- ✅ **Cleaned transactions** — normalised dates, stripped currency symbols, uppercased statuses, filled categories, deduplicated rows
- ✅ **Flagged anomalies** — statistical outliers (>3× account median) and currency mismatches (USD on domestic merchants)
- ✅ **LLM classification** — batch-categorised uncategorised transactions via Gemini
- ✅ **Structured narrative summary** — LLM-generated spending narrative with risk level and per-category breakdown

---

## Architecture

```
┌──────────────┐       ┌───────────────────┐       ┌─────────────────┐
│   Client     │──────▶│   FastAPI (API)   │──────▶│  Redis (Queue)  │
└──────────────┘       └───────────────────┘       └────────┬────────┘
                               │                            │
                               ▼                            ▼
                       ┌───────────────┐          ┌─────────────────┐
                       │  PostgreSQL   │◀─────────│ Celery (Worker) │
                       └───────────────┘          └─────────────────┘
                                                          │
                                              ┌───────────▼────────────┐
                                              │  Processing Pipeline   │
                                              │  1. Data Cleaning      │
                                              │  2. Anomaly Detection  │
                                              │  3. LLM Classification │
                                              │  4. LLM Narrative      │
                                              └────────────────────────┘
```

**Request Lifecycle:**
1. Client uploads CSV → FastAPI validates (extension, size, required columns), saves file, creates `Job` record (`status: pending`), pushes task to Redis
2. Celery worker dequeues task, runs the 4-step pipeline
3. Transactions + `JobSummary` bulk-inserted into PostgreSQL (`status: completed`)
4. Client polls `/status` then fetches full results from `/results`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI 0.110 |
| Task Queue | Celery 5.3 + Redis 7 |
| Database | PostgreSQL 15 + SQLAlchemy 2.0 |
| LLM | Google Gemini (`gemini-2.0-flash`) |
| Data Processing | Pandas 2.2 |
| Containerisation | Docker + Docker Compose |
| Testing | Pytest + HTTPX |

**Architectural patterns:** Repository layer · Service layer · Versioned API (`/api/v1`) · Global exception middleware · Structured response envelope

---

## Project Structure

```
.
├── app/
│   ├── api/v1/endpoints/     # Route handlers
│   ├── core/                 # Config, Celery app, exceptions
│   ├── db/                   # SQLAlchemy models, session
│   ├── llm/                  # Gemini client (batch classify + narrative)
│   ├── middleware/            # Global error handler
│   ├── repository/           # DB access layer
│   ├── response/             # Response DTOs
│   ├── schema/               # Pydantic schemas
│   ├── services/             # Business logic (pipeline orchestration)
│   ├── utils/                # DataCleaner
│   ├── worker/               # Celery task definition
│   └── main.py               # FastAPI app entrypoint
├── tests/
│   ├── conftest.py
│   └── test_pipeline.py      # Unit + integration tests
├── docs/
│   └── transactions.csv      # Sample input file
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### 1. Clone the repository
```bash
git clone https://github.com/sidhyaashu/Alemeno.git
cd Alemeno
```

### 2. Configure environment
```bash
cp .env.example .env
```

Open `.env` and add your Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

> **Note:** The pipeline works without a Gemini key — LLM steps will be skipped and transactions marked `llm_failed=true`. All other pipeline stages (cleaning, anomaly detection, summary stats) run normally.

### 3. Start all services
```bash
docker compose up --build
```

This spins up **PostgreSQL**, **Redis**, **FastAPI API**, and **Celery Worker** in one command. Health checks ensure services start in the correct order.

The API is available at: **http://localhost:8000**

Interactive docs: **http://localhost:8000/docs**

---

## API Reference

All endpoints are versioned under `/api/v1`.

### `POST /api/v1/jobs/upload`
Upload a CSV file for async processing.

**Validations:** `.csv` extension · non-empty · ≤ 10 MB · all required columns present

```bash
curl -X POST "http://localhost:8000/api/v1/jobs/upload" \
  -F "file=@docs/transactions.csv"
```

**Response:**
```json
{
  "status": "success",
  "data": { "job_id": "uuid-...", "status": "pending" },
  "message": "Job created and queued successfully."
}
```

---

### `GET /api/v1/jobs/{job_id}/status`
Poll job status. Status values: `pending` → `processing` → `completed` / `failed`

```bash
curl "http://localhost:8000/api/v1/jobs/<JOB_ID>/status"
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "id": "uuid-...",
    "filename": "transactions.csv",
    "status": "completed",
    "row_count_raw": 92,
    "row_count_clean": 89,
    "created_at": "2024-01-15T10:00:00Z",
    "completed_at": "2024-01-15T10:00:12Z",
    "summary": {
      "total_spend_inr": 145000.0,
      "total_spend_usd": 890.5,
      "anomaly_count": 4,
      "narrative": "The account shows heavy domestic spending...",
      "risk_level": "medium"
    }
  }
}
```

---

### `GET /api/v1/jobs/{job_id}/results`
Retrieve full structured output.

```bash
curl "http://localhost:8000/api/v1/jobs/<JOB_ID>/results"
```

**Response shape:**
```json
{
  "status": "success",
  "data": {
    "id": "...",
    "status": "completed",
    "row_count_raw": 92,
    "row_count_clean": 89,
    "transactions": [ ... ],
    "anomalies": [ ... ],
    "summary": {
      "total_spend_inr": 145000.0,
      "total_spend_usd": 890.5,
      "top_merchants": [
        { "merchant": "Amazon", "total": 45000.0 },
        { "merchant": "Swiggy", "total": 12000.0 },
        { "merchant": "IRCTC",  "total": 8500.0 }
      ],
      "anomaly_count": 4,
      "category_breakdown": {
        "Food": 12000.0,
        "Travel": 8500.0,
        "Shopping": 45000.0
      },
      "narrative": "Spending is concentrated in e-commerce and food delivery...",
      "risk_level": "medium",
      "llm_failed": false
    }
  }
}
```

---

### `GET /api/v1/jobs?status=<status>`
List all jobs. Optional `?status=` filter.

```bash
# All jobs
curl "http://localhost:8000/api/v1/jobs"

# Only completed jobs
curl "http://localhost:8000/api/v1/jobs?status=completed"

# Only failed jobs
curl "http://localhost:8000/api/v1/jobs?status=failed"
```

---

## Processing Pipeline

When a job is dequeued, the Celery worker executes these steps in order:

### 1. Data Cleaning
| Operation | Detail |
|-----------|--------|
| Date normalisation | Any format → ISO 8601 (`YYYY-MM-DD`) via `pd.to_datetime(infer_datetime_format=True)` |
| Amount parsing | Strips `$`, `₹`, `€`, `£`, `,` — invalid values stored as `null` (not `0`) |
| Status / currency | Uppercased and stripped |
| Missing categories | Filled with `"Uncategorised"` |
| Duplicate removal | Exact duplicate rows dropped |

### 2. Anomaly Detection
| Rule | Condition |
|------|-----------|
| Statistical outlier | `amount > 3 × account median` |
| Currency mismatch | `currency = USD` AND merchant is a domestic brand (Swiggy, Ola, IRCTC, Zomato, etc.) — case-insensitive |

### 3. LLM Batch Classification
Uncategorised transactions are batched into a single Gemini API call. Categories: `Food · Shopping · Travel · Transport · Utilities · Cash Withdrawal · Entertainment · Other`

### 4. LLM Narrative Summary
A single Gemini call produces a structured JSON with all 5 required fields: `total_spend_by_currency`, `top_3_merchants`, `anomaly_count`, `narrative`, `risk_level`.

### Retry Logic
Both LLM calls retry up to **3 times with exponential backoff** (`1s → 2s → 4s`). On total failure, the batch is marked `llm_failed=true` and the pipeline continues — the job never fails due to LLM errors alone.

---

## Scalability & Bottlenecks

### Current Limitations (at 100× traffic)

| Bottleneck | Impact | Production Fix |
|------------|--------|---------------|
| `pd.read_csv()` loads entire file into RAM | OOM crash on large CSVs | Chunked processing with `pd.read_csv(chunksize=N)` or Dask/Polars |
| LLM token limits | Large batches exceed context window | Split batches, use Celery chord for parallel sub-tasks |
| PostgreSQL connection pool | Worker fleet saturates `max_connections` | PgBouncer connection pooler; use PostgreSQL `COPY` instead of ORM bulk save |
| Local file storage (`uploads/`) | Files lost on container restart | Move to S3/GCS with pre-signed upload URLs |
| Single Celery queue | No task priority isolation | Separate `high-priority` and `low-priority` queues with routing |

### What Would Change for Enterprise Scale
- Replace `create_all()` with **Alembic migrations** for zero-downtime schema changes
- Add **Flower** or **Prometheus + Grafana** for worker observability
- Switch to **async SQLAlchemy** (`asyncpg`) to unblock the API during DB I/O
- Add **rate limiting** (e.g., `slowapi`) on the upload endpoint

---

## Running Tests

```bash
# Install dependencies locally (or run inside the container)
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run only DataCleaner unit tests
pytest tests/ -v -k "TestDataCleaner"

# Run only API validation tests
pytest tests/ -v -k "TestUploadEndpoint"
```

Tests cover:
- Date normalisation (multiple formats)
- Amount parsing (currency symbols, commas)
- Status / currency uppercasing
- Missing category fill
- Duplicate row removal
- Anomaly detection (3× median, case-insensitive domestic merchant check)
- API: invalid extension, empty file, missing columns, oversized file, 404 responses
