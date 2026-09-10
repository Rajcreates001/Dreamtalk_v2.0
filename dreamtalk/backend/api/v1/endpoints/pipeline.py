"""Pipeline API Endpoints — Face + Voice + Brain + Object Detection end-to-end."""

import json
import logging
import os
import uuid
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse

from dreamtalk.backend.api.v1.endpoints.auth import get_current_user
from dreamtalk.backend.db.database import execute, fetchrow
from dreamtalk.pipeline.models import (
    PipelineRequest,
    PipelineResult,
    PipelineStatus,
    FaceAnalysisResult,
    VoiceAnalysisResult,
    EmotionResult,
    BrainDecisionResult,
    ObjectDetectionResult,
)
from dreamtalk.pipeline.orchestrator import PipelineOrchestrator

logger = logging.getLogger("dreamtalk.api.pipeline")

router = APIRouter(prefix="/api/v1/pipeline", tags=["Digital Twin Pipeline"])
orchestrator = PipelineOrchestrator()


@router.post("/run", response_model=PipelineResult)
async def run_pipeline(
    req: PipelineRequest,
    current_user: dict = Depends(get_current_user),
):
    """Run the full end-to-end pipeline: Face → Voice → Emotion → Brain → Object Detection.

    Provide image_paths and/or voice_paths and/or text_input.
    Pipeline auto-detects which stages to run based on available inputs.
    """
    if not req.twin_id:
        req.twin_id = str(uuid.uuid4())

    result = await orchestrator.run_full_pipeline(req)
    return result


@router.post("/run-with-uploads", response_model=PipelineResult)
async def run_pipeline_with_uploads(
    text_input: str = Form(""),
    role: str = Form("normal_user"),
    twin_id: str = Form(""),
    model_name: str = Form("deepseek"),
    enable_3d_face: bool = Form(True),
    enable_voice_clone: bool = Form(True),
    enable_emotion: bool = Form(True),
    enable_decision: bool = Form(True),
    enable_object_detection: bool = Form(False),
    image_files: List[UploadFile] = File(default=[]),
    voice_files: List[UploadFile] = File(default=[]),
    current_user: dict = Depends(get_current_user),
):
    """Run pipeline with uploaded files (multipart form).

    Upload images and/or voice files, provide optional text input.
    Files are saved to temp storage before processing.
    """
    upload_dir = "pipeline_uploads"
    os.makedirs(upload_dir, exist_ok=True)

    image_paths = []
    for f in image_files:
        ext = os.path.splitext(f.filename or "image.jpg")[1] or ".jpg"
        path = os.path.join(upload_dir, f"img_{uuid.uuid4().hex}{ext}")
        content = await f.read()
        with open(path, "wb") as fh:
            fh.write(content)
        image_paths.append(path)

    voice_paths = []
    for f in voice_files:
        ext = os.path.splitext(f.filename or "audio.wav")[1] or ".wav"
        path = os.path.join(upload_dir, f"voice_{uuid.uuid4().hex}{ext}")
        content = await f.read()
        with open(path, "wb") as fh:
            fh.write(content)
        voice_paths.append(path)

    if not twin_id:
        twin_id = str(uuid.uuid4())

    req = PipelineRequest(
        twin_id=twin_id,
        user_id=current_user.get("sub", ""),
        role=role,
        image_paths=image_paths,
        voice_paths=voice_paths,
        text_input=text_input,
        enable_3d_face=enable_3d_face,
        enable_voice_clone=enable_voice_clone,
        enable_emotion=enable_emotion,
        enable_decision=enable_decision,
        enable_object_detection=enable_object_detection,
        model_name=model_name,
    )

    result = await orchestrator.run_full_pipeline(req)
    return result


@router.post("/face", response_model=FaceAnalysisResult)
async def run_face_pipeline(
    req: PipelineRequest,
    current_user: dict = Depends(get_current_user),
):
    """Run only the Face Analysis pipeline."""
    result = await orchestrator.run_face_only(req)
    return result


@router.post("/voice", response_model=VoiceAnalysisResult)
async def run_voice_pipeline(
    req: PipelineRequest,
    current_user: dict = Depends(get_current_user),
):
    """Run only the Voice Analysis pipeline."""
    result = await orchestrator.run_voice_only(req)
    return result


@router.post("/decision", response_model=dict)
async def run_decision_pipeline(
    req: PipelineRequest,
    current_user: dict = Depends(get_current_user),
):
    """Run only the Brain/Decision pipeline (emotion + decision + optional object detection)."""
    result = await orchestrator.run_decision_only(req)
    return result


@router.get("/results/{pipeline_id}", response_model=dict)
async def get_pipeline_result(
    pipeline_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Retrieve a saved pipeline result from the database."""
    try:
        row = await fetchrow(
            "SELECT result_data FROM pipeline_results WHERE pipeline_id = $1",
            pipeline_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Pipeline result not found")
        return row["result_data"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{twin_id}", response_model=List[dict])
async def list_pipeline_history(
    twin_id: str,
    current_user: dict = Depends(get_current_user),
):
    """List all pipeline results for a given twin."""
    try:
        from dreamtalk.backend.db.database import fetch
        rows = await fetch(
            """SELECT pipeline_id, result_type, result_data, created_at
               FROM pipeline_results
               WHERE twin_id = $1
               ORDER BY created_at DESC
               LIMIT 50""",
            twin_id,
        )
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"History lookup failed: {e}")
        return []
