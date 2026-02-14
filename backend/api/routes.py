import uuid
import json
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from backend.config import settings
from backend.models.pipeline import Job, JobStatus, ProductProgress, ProductStatus
from backend.agents.ingestion import IngestionAgent
from backend.pipeline.worker import WorkerManager

router = APIRouter(prefix="/api")

# In-memory store for active worker managers
active_jobs: dict[str, WorkerManager] = {}


class StartJobRequest(BaseModel):
    llm_provider: str = "deepseek"
    workers: int = 10


class SettingsUpdate(BaseModel):
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    deepseek_api_key: str | None = None
    default_llm: str | None = None
    default_workers: int | None = None


# ─── Upload ───

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a product data file (CSV, JSON, Excel)."""
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".csv", ".json", ".xlsx", ".xls"):
        raise HTTPException(400, f"Unsupported file format: {suffix}. Use CSV, JSON, or Excel.")

    # Save uploaded file
    job_id = uuid.uuid4().hex[:12]
    file_path = settings.UPLOAD_DIR / f"{job_id}_{file.filename}"

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Read products to get count
    ingestion = IngestionAgent()
    try:
        products = await ingestion.run(str(file_path))
    except Exception as e:
        raise HTTPException(400, f"Failed to read file: {e}")

    # Create job
    job = Job(
        id=job_id,
        filename=file.filename,
        total_products=len(products),
        products=[
            ProductProgress(product_id=p.id, title=p.title)
            for p in products
        ],
    )

    # Save job to disk
    job_path = settings.JOBS_DIR / f"{job_id}.json"
    with open(job_path, "w") as f:
        f.write(job.model_dump_json(indent=2))

    return {
        "job_id": job_id,
        "filename": file.filename,
        "total_products": len(products),
    }


# ─── Jobs ───

@router.get("/jobs")
async def list_jobs():
    """List all jobs."""
    jobs = []
    for job_file in settings.JOBS_DIR.glob("*.json"):
        with open(job_file) as f:
            job = Job.model_validate_json(f.read())
            jobs.append({
                "id": job.id,
                "filename": job.filename,
                "status": job.status,
                "total_products": job.total_products,
                "completed_products": job.completed_products,
                "failed_products": job.failed_products,
                "created_at": str(job.created_at),
            })
    return jobs


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job details and progress."""
    job = _load_job(job_id)
    return job.model_dump()


@router.post("/jobs/{job_id}/start")
async def start_job(job_id: str, request: StartJobRequest):
    """Start processing a job."""
    job = _load_job(job_id)

    if job.status == JobStatus.RUNNING:
        raise HTTPException(400, "Job is already running")

    # Validate workers
    workers = min(max(1, request.workers), settings.MAX_WORKERS)
    job.llm_provider = request.llm_provider
    job.workers = workers

    # Load products from file
    upload_files = list(settings.UPLOAD_DIR.glob(f"{job_id}_*"))
    if not upload_files:
        raise HTTPException(404, "Upload file not found for this job")

    ingestion = IngestionAgent()
    products = await ingestion.run(str(upload_files[0]))

    # Create worker manager and start
    manager = WorkerManager(job)
    active_jobs[job_id] = manager

    import asyncio
    asyncio.create_task(manager.start(products))

    return {"status": "started", "workers": workers, "llm_provider": request.llm_provider}


@router.post("/jobs/{job_id}/stop")
async def stop_job(job_id: str):
    """Stop a running job."""
    if job_id not in active_jobs:
        raise HTTPException(404, "Job is not currently running")

    await active_jobs[job_id].stop()
    del active_jobs[job_id]

    return {"status": "stopped"}


@router.get("/jobs/{job_id}/products")
async def get_job_products(job_id: str):
    """Get product list with per-product status."""
    job = _load_job(job_id)
    return [p.model_dump() for p in job.products]


@router.get("/jobs/{job_id}/export")
async def export_job(job_id: str):
    """Download the Matrixify CSV for a completed job."""
    job = _load_job(job_id)

    if not job.output_file:
        raise HTTPException(404, "No export file available yet")

    output_path = Path(job.output_file)
    if not output_path.exists():
        raise HTTPException(404, "Export file not found on disk")

    return FileResponse(
        output_path,
        media_type="text/csv",
        filename=f"litterly_{job_id}_matrixify.csv",
    )


# ─── Settings ───

@router.get("/settings")
async def get_settings():
    """Get current settings."""
    return {
        "available_providers": settings.get_available_providers(),
        "default_llm": settings.DEFAULT_LLM,
        "default_workers": settings.DEFAULT_WORKERS,
        "max_workers": settings.MAX_WORKERS,
        "has_openai_key": bool(settings.OPENAI_API_KEY),
        "has_anthropic_key": bool(settings.ANTHROPIC_API_KEY),
        "has_gemini_key": bool(settings.GEMINI_API_KEY),
        "has_deepseek_key": bool(settings.DEEPSEEK_API_KEY),
    }


@router.post("/settings")
async def update_settings(update: SettingsUpdate):
    """Update settings (saves to .env file)."""
    env_path = settings.ROOT_DIR / ".env"
    lines = []

    if env_path.exists():
        with open(env_path) as f:
            lines = f.readlines()

    def set_env_value(key: str, value: str):
        nonlocal lines
        found = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                found = True
                break
        if not found:
            lines.append(f"{key}={value}\n")

    if update.openai_api_key is not None:
        set_env_value("OPENAI_API_KEY", update.openai_api_key)
        settings.OPENAI_API_KEY = update.openai_api_key

    if update.anthropic_api_key is not None:
        set_env_value("ANTHROPIC_API_KEY", update.anthropic_api_key)
        settings.ANTHROPIC_API_KEY = update.anthropic_api_key

    if update.gemini_api_key is not None:
        set_env_value("GEMINI_API_KEY", update.gemini_api_key)
        settings.GEMINI_API_KEY = update.gemini_api_key

    if update.deepseek_api_key is not None:
        set_env_value("DEEPSEEK_API_KEY", update.deepseek_api_key)
        settings.DEEPSEEK_API_KEY = update.deepseek_api_key

    if update.default_llm is not None:
        settings.DEFAULT_LLM = update.default_llm

    if update.default_workers is not None:
        settings.DEFAULT_WORKERS = min(max(1, update.default_workers), settings.MAX_WORKERS)

    with open(env_path, "w") as f:
        f.writelines(lines)

    return {"status": "updated"}


# ─── Helpers ───

def _load_job(job_id: str) -> Job:
    """Load a job from disk."""
    job_path = settings.JOBS_DIR / f"{job_id}.json"
    if not job_path.exists():
        raise HTTPException(404, f"Job {job_id} not found")
    with open(job_path) as f:
        return Job.model_validate_json(f.read())
