import uuid
import json
import logging
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from backend.config import settings
from backend.models.pipeline import Job, JobStatus, ProductProgress, ProductStatus
from backend.agents.ingestion import IngestionAgent
from backend.agents.chat import ChatAgent
from backend.llm import get_llm
from backend.pipeline.worker import WorkerManager

logger = logging.getLogger("litterly.api")

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


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []


# ─── Upload ───

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a product data file (CSV, JSON, Excel)."""
    logger.info(f"[UPLOAD] Received file: {file.filename} (size: {file.size} bytes, type: {file.content_type})")

    if not file.filename:
        logger.error("[UPLOAD] No filename provided")
        raise HTTPException(400, "No filename provided")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".csv", ".json", ".xlsx", ".xls"):
        logger.error(f"[UPLOAD] Unsupported format: {suffix}")
        raise HTTPException(400, f"Unsupported file format: {suffix}. Use CSV, JSON, or Excel.")

    # Save uploaded file
    job_id = uuid.uuid4().hex[:12]
    file_path = settings.UPLOAD_DIR / f"{job_id}_{file.filename}"

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"[UPLOAD] File saved to: {file_path} ({len(content)} bytes)")

    # Read products to get count
    logger.info(f"[UPLOAD] Parsing file to detect products...")
    ingestion = IngestionAgent()
    try:
        products = await ingestion.run(str(file_path))
    except Exception as e:
        logger.error(f"[UPLOAD] Failed to parse file: {e}")
        raise HTTPException(400, f"Failed to read file: {e}")

    logger.info(f"[UPLOAD] Detected {len(products)} products in file")
    for i, p in enumerate(products):
        logger.debug(f"[UPLOAD]   Product {i+1}: id={p.id}, title='{p.title[:50]}', brand='{p.brand}'")

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

    logger.info(f"[UPLOAD] Job created: id={job_id}, products={len(products)}, saved to {job_path}")

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
                "job_folder": job.job_folder,
                "has_output": job.output_file is not None,
            })

    logger.debug(f"[JOBS] Listed {len(jobs)} jobs")
    return jobs


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job details and progress."""
    logger.debug(f"[JOBS] Fetching job: {job_id}")
    job = _load_job(job_id)
    return job.model_dump()


@router.post("/jobs/{job_id}/start")
async def start_job(job_id: str, request: StartJobRequest):
    """Start processing a job."""
    logger.info(f"[START] Starting job {job_id} — LLM: {request.llm_provider}, Workers: {request.workers}")

    job = _load_job(job_id)

    if job.status == JobStatus.RUNNING:
        logger.warning(f"[START] Job {job_id} is already running!")
        raise HTTPException(400, "Job is already running")

    # Validate workers
    workers = min(max(1, request.workers), settings.MAX_WORKERS)
    job.llm_provider = request.llm_provider
    job.workers = workers

    logger.info(f"[START] Job config — LLM: {request.llm_provider}, Workers: {workers} (max: {settings.MAX_WORKERS})")

    # Load products from file
    upload_files = list(settings.UPLOAD_DIR.glob(f"{job_id}_*"))
    if not upload_files:
        logger.error(f"[START] No upload file found for job {job_id}")
        raise HTTPException(404, "Upload file not found for this job")

    logger.info(f"[START] Loading products from: {upload_files[0]}")

    ingestion = IngestionAgent()
    products = await ingestion.run(str(upload_files[0]))

    logger.info(f"[START] Loaded {len(products)} products, creating worker manager...")

    # Create worker manager and start
    manager = WorkerManager(job)
    active_jobs[job_id] = manager

    logger.info(f"[START] Job folder created: {manager.job_folder}")
    logger.info(f"[START] Live CSV path: {manager.live_csv_path}")
    logger.info(f"[START] Final CSV path: {manager.final_csv_path}")
    logger.info(f"[START] Launching {workers} workers for {len(products)} products...")

    import asyncio
    asyncio.create_task(manager.start(products))

    logger.info(f"[START] Job {job_id} is now RUNNING")

    return {"status": "started", "workers": workers, "llm_provider": request.llm_provider}


@router.post("/jobs/{job_id}/stop")
async def stop_job(job_id: str):
    """Stop a running job."""
    logger.info(f"[STOP] Stopping job {job_id}...")

    if job_id not in active_jobs:
        logger.error(f"[STOP] Job {job_id} is not currently running")
        raise HTTPException(404, "Job is not currently running")

    await active_jobs[job_id].stop()
    del active_jobs[job_id]

    logger.info(f"[STOP] Job {job_id} stopped successfully")

    return {"status": "stopped"}


@router.get("/jobs/{job_id}/products")
async def get_job_products(job_id: str):
    """Get product list with per-product status."""
    job = _load_job(job_id)
    return [p.model_dump() for p in job.products]


@router.get("/jobs/{job_id}/export")
async def export_job(job_id: str):
    """Download the Matrixify CSV for a completed job."""
    logger.info(f"[EXPORT] Final CSV download requested for job {job_id}")

    job = _load_job(job_id)

    if not job.output_file:
        logger.warning(f"[EXPORT] No output file for job {job_id} yet")
        raise HTTPException(404, "No export file available yet")

    output_path = Path(job.output_file)
    if not output_path.exists():
        logger.error(f"[EXPORT] File not found on disk: {output_path}")
        raise HTTPException(404, "Export file not found on disk")

    file_size = output_path.stat().st_size
    logger.info(f"[EXPORT] Serving final CSV: {output_path} ({file_size} bytes)")

    return FileResponse(
        output_path,
        media_type="text/csv",
        filename=f"litterly_{job_id}_matrixify.csv",
    )


@router.get("/jobs/{job_id}/export/live")
async def export_job_live(job_id: str):
    """Download the live (in-progress) CSV for a running job."""
    logger.info(f"[EXPORT] Live CSV download requested for job {job_id}")

    job = _load_job(job_id)

    if not job.job_folder:
        logger.warning(f"[EXPORT] No job folder for job {job_id}")
        raise HTTPException(404, "No job folder found")

    live_path = Path(job.job_folder) / "matrixify_live.csv"
    if not live_path.exists():
        logger.warning(f"[EXPORT] Live CSV not found: {live_path}")
        raise HTTPException(404, "No live CSV available yet — no products completed")

    file_size = live_path.stat().st_size
    logger.info(f"[EXPORT] Serving live CSV: {live_path} ({file_size} bytes)")

    return FileResponse(
        live_path,
        media_type="text/csv",
        filename=f"litterly_{job_id}_live.csv",
    )


# ─── Chat ───

@router.post("/jobs/{job_id}/chat")
async def chat(job_id: str, request: ChatRequest):
    """Chat with Litterly about this job."""
    logger.info(f"[CHAT] Message for job {job_id}: {request.message[:80]}...")

    job = _load_job(job_id)

    # Use the job's LLM provider
    llm = get_llm(job.llm_provider)
    chat_agent = ChatAgent(llm=llm)

    try:
        response = await chat_agent.run({
            "message": request.message,
            "job_id": job_id,
            "conversation_history": request.conversation_history,
        })

        logger.info(f"[CHAT] Response generated ({len(response)} chars)")
        return {"response": response, "job_id": job_id}

    except Exception as e:
        logger.error(f"[CHAT] Error: {e}")
        raise HTTPException(500, f"Chat failed: {e}")


# ─── Settings ───

@router.get("/settings")
async def get_settings():
    """Get current settings."""
    logger.debug("[SETTINGS] Fetching current settings")
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
    logger.info("[SETTINGS] Updating settings...")

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
        logger.info("[SETTINGS] OpenAI API key updated")

    if update.anthropic_api_key is not None:
        set_env_value("ANTHROPIC_API_KEY", update.anthropic_api_key)
        settings.ANTHROPIC_API_KEY = update.anthropic_api_key
        logger.info("[SETTINGS] Anthropic API key updated")

    if update.gemini_api_key is not None:
        set_env_value("GEMINI_API_KEY", update.gemini_api_key)
        settings.GEMINI_API_KEY = update.gemini_api_key
        logger.info("[SETTINGS] Gemini API key updated")

    if update.deepseek_api_key is not None:
        set_env_value("DEEPSEEK_API_KEY", update.deepseek_api_key)
        settings.DEEPSEEK_API_KEY = update.deepseek_api_key
        logger.info("[SETTINGS] DeepSeek API key updated")

    if update.default_llm is not None:
        settings.DEFAULT_LLM = update.default_llm
        logger.info(f"[SETTINGS] Default LLM changed to: {update.default_llm}")

    if update.default_workers is not None:
        settings.DEFAULT_WORKERS = min(max(1, update.default_workers), settings.MAX_WORKERS)
        logger.info(f"[SETTINGS] Default workers changed to: {settings.DEFAULT_WORKERS}")

    with open(env_path, "w") as f:
        f.writelines(lines)

    logger.info(f"[SETTINGS] Settings saved to {env_path}")

    return {"status": "updated"}


# ─── Helpers ───

def _load_job(job_id: str) -> Job:
    """Load a job from disk."""
    job_path = settings.JOBS_DIR / f"{job_id}.json"
    if not job_path.exists():
        logger.error(f"[JOBS] Job not found: {job_id} (looked at {job_path})")
        raise HTTPException(404, f"Job {job_id} not found")
    with open(job_path) as f:
        return Job.model_validate_json(f.read())
