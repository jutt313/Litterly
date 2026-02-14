import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
from backend.config import settings
from backend.models.pipeline import Job


class ConnectionManager:
    """Manages WebSocket connections for real-time progress updates."""

    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        if job_id not in self.connections:
            self.connections[job_id] = []
        self.connections[job_id].append(websocket)

    def disconnect(self, websocket: WebSocket, job_id: str):
        if job_id in self.connections:
            self.connections[job_id] = [
                ws for ws in self.connections[job_id] if ws != websocket
            ]

    async def broadcast_job_update(self, job_id: str):
        """Send current job state to all connected clients."""
        if job_id not in self.connections:
            return

        job_path = settings.JOBS_DIR / f"{job_id}.json"
        if not job_path.exists():
            return

        with open(job_path) as f:
            job = Job.model_validate_json(f.read())

        message = json.dumps({
            "type": "job_update",
            "data": {
                "id": job.id,
                "status": job.status,
                "total_products": job.total_products,
                "completed_products": job.completed_products,
                "failed_products": job.failed_products,
                "products": [p.model_dump(mode="json") for p in job.products],
            },
        }, default=str)

        dead_connections = []
        for ws in self.connections[job_id]:
            try:
                await ws.send_text(message)
            except Exception:
                dead_connections.append(ws)

        for ws in dead_connections:
            self.disconnect(ws, job_id)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job progress."""
    await manager.connect(websocket, job_id)

    try:
        while True:
            # Send updates every 2 seconds
            await manager.broadcast_job_update(job_id)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id)
