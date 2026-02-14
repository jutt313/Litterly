import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router
from backend.api.websocket import websocket_endpoint

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

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
