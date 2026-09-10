# ── Celery Task API ───────────────────────────────────────────────────
# Endpoints to submit and check async tasks.

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("dreamtalk.celery_api")

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# Check if celery is available
_celery = None
try:
    from dreamtalk.backend.celery_app import celery_app as _celery
except Exception:
    pass


class PipelineTaskRequest(BaseModel):
    image_path: str
    voice_path: str
    twin_id: Optional[str] = None


class TTSTaskRequest(BaseModel):
    text: str
    language: str = "en"
    voice: Optional[str] = None


class BrainTaskRequest(BaseModel):
    text: str
    twin_id: Optional[str] = None
    language: str = "en"


@router.post("/pipeline")
async def submit_pipeline(req: PipelineTaskRequest):
    """Submit a full pipeline task to the Celery worker."""
    if not _celery:
        raise HTTPException(status_code=503, detail="Celery not available")
    from dreamtalk.backend.celery_tasks import run_full_pipeline
    task = run_full_pipeline.delay(
        image_path=req.image_path,
        voice_path=req.voice_path,
        twin_id=req.twin_id,
    )
    return {"task_id": task.id, "status": "submitted"}


@router.post("/tts")
async def submit_tts(req: TTSTaskRequest):
    """Submit a TTS generation task to the Celery worker."""
    if not _celery:
        raise HTTPException(status_code=503, detail="Celery not available")
    from dreamtalk.backend.celery_tasks import generate_tts_async
    task = generate_tts_async.delay(
        text=req.text,
        language=req.language,
        voice=req.voice,
    )
    return {"task_id": task.id, "status": "submitted"}


@router.post("/brain")
async def submit_brain(req: BrainTaskRequest):
    """Submit a brain/LLM inference task to the Celery worker."""
    if not _celery:
        raise HTTPException(status_code=503, detail="Celery not available")
    from dreamtalk.backend.celery_tasks import run_brain_inference
    task = run_brain_inference.delay(
        text=req.text,
        twin_id=req.twin_id,
        language=req.language,
    )
    return {"task_id": task.id, "status": "submitted"}


@router.get("/result/{task_id}")
async def get_task_result(task_id: str):
    """Get the result of an async task."""
    if not _celery:
        raise HTTPException(status_code=503, detail="Celery not available")
    result = _celery.AsyncResult(task_id)
    if result.pending:
        return {"task_id": task_id, "status": "pending"}
    if result.failed():
        return {"task_id": task_id, "status": "failed", "error": str(result.info)}
    return {
        "task_id": task_id,
        "status": "completed",
        "result": result.result,
    }
