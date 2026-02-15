import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router
from backend.api.websocket import websocket_endpoint
from backend.config import settings
import time

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("litterly")

app = FastAPI(
    title="Litterly",
    description="AI-powered product data enrichment pipeline for e-commerce",
    version="0.1.0",
)

# CORS — allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request/Response logging middleware ───

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f">>> {request.method} {request.url.path}")

    response = await call_next(request)

    duration = round((time.time() - start_time) * 1000, 1)
    logger.info(f"<<< {request.method} {request.url.path} — {response.status_code} ({duration}ms)")

    return response


# ─── Startup / Shutdown events ───

@app.on_event("startup")
async def on_startup():
    logger.info("=" * 60)
    logger.info("  LITTERLY v0.1.0 — Starting up...")
    logger.info("=" * 60)

    # Log config
    providers = settings.get_available_providers()
    logger.info(f"  Upload dir:     {settings.UPLOAD_DIR}")
    logger.info(f"  Output dir:     {settings.OUTPUT_DIR}")
    logger.info(f"  Jobs dir:       {settings.JOBS_DIR}")
    logger.info(f"  Prompts dir:    {settings.PROMPTS_DIR}")
    logger.info(f"  Default LLM:    {settings.DEFAULT_LLM}")
    logger.info(f"  Default workers:{settings.DEFAULT_WORKERS}")
    logger.info(f"  Max workers:    {settings.MAX_WORKERS}")

    # Log API key status
    logger.info(f"  DeepSeek key:   {'configured' if settings.DEEPSEEK_API_KEY else 'MISSING'}")
    logger.info(f"  OpenAI key:     {'configured' if settings.OPENAI_API_KEY else 'MISSING'}")
    logger.info(f"  Claude key:     {'configured' if settings.ANTHROPIC_API_KEY else 'MISSING'}")
    logger.info(f"  Gemini key:     {'configured' if settings.GEMINI_API_KEY else 'MISSING'}")
    logger.info(f"  Available LLMs: {providers if providers else 'NONE — add API keys!'}")

    # Count existing jobs
    existing_jobs = list(settings.JOBS_DIR.glob("*.json"))
    logger.info(f"  Past jobs:      {len(existing_jobs)}")

    logger.info("=" * 60)
    logger.info("  Ready! Open http://localhost:3000 in your browser")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Litterly shutting down... Goodbye!")


# API routes
app.include_router(router)

# WebSocket
app.websocket("/ws/progress/{job_id}")(websocket_endpoint)


@app.get("/")
async def root():
    return {"name": "Litterly", "version": "0.1.0", "status": "running"}


def start():
    """Entry point for `litterly` CLI command."""
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
