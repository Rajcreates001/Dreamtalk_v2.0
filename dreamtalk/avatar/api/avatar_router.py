# Dreamtalk - Avatar Module
# Migrated from Dreamtalk-Avatar-Module

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dreamtalk.avatar.services.avatar_service import AvatarService
from dreamtalk.avatar.core.renderer import ImageProcessingService
from dreamtalk.avatar.core.face_swap import FaceReconstructionService
from dreamtalk.avatar.core.pipeline import settings
from dreamtalk.avatar.models.avatar_schemas import (
    AvatarGenerateResponse,
    EnhanceImageResponse,
    ReconstructFaceResponse,
    ProgressResponse,
    StatusResponse,
)
import os

router = APIRouter(prefix="/api/avatar", tags=["avatar"])

orchestrator = AvatarService()
image_service = ImageProcessingService()
face_service = FaceReconstructionService()


@router.post("/generate-avatar", response_model=AvatarGenerateResponse)
async def generate_avatar(
    text: str = Form(...),
    emotion: str = Form("neutral"),
    image: UploadFile = File(...)
):
    """
    Full avatar pipeline endpoint.
    Uploads an image, processes it, and returns avatar output.
    """
    try:
        os.makedirs(settings.ASSETS_AVATARS_DIR, exist_ok=True)

        temp_image_path = os.path.join(
            settings.ASSETS_AVATARS_DIR,
            image.filename
        )

        with open(temp_image_path, "wb") as buffer:
            buffer.write(await image.read())

        result = await orchestrator.run_full_pipeline(
            image_path=temp_image_path,
            text=text,
            emotion=emotion
        )

        if result.get("status") == "error":
            raise HTTPException(
                status_code=500,
                detail=result.get("message")
            )

        return result

    except HTTPException:
        raise

    except Exception as e:
        import traceback
        print("GENERATE AVATAR ERROR:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enhance-image", response_model=EnhanceImageResponse)
async def enhance_image(image: UploadFile = File(...)):
    """
    Independent endpoint for face restoration and super-resolution.
    """
    try:
        os.makedirs(settings.ASSETS_AVATARS_DIR, exist_ok=True)

        temp_path = os.path.join(
            settings.ASSETS_AVATARS_DIR,
            image.filename
        )

        with open(temp_path, "wb") as buffer:
            buffer.write(await image.read())

        enhanced_path = await image_service.enhance_face(temp_path)

        filename = os.path.basename(enhanced_path)

        return {
            "status": "success",
            "enhanced_image_path": enhanced_path,
            "enhanced_image_url": f"/avatars/{filename}"
        }

    except Exception as e:
        import traceback
        print("ENHANCE IMAGE ERROR:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reconstruct-face", response_model=ReconstructFaceResponse)
async def reconstruct_face(image: UploadFile = File(...)):
    """
    Independent endpoint for 3D face reconstruction.
    """
    try:
        os.makedirs(settings.ASSETS_AVATARS_DIR, exist_ok=True)

        temp_path = os.path.join(
            settings.ASSETS_AVATARS_DIR,
            image.filename
        )

        with open(temp_path, "wb") as buffer:
            buffer.write(await image.read())

        reconstruction = await face_service.reconstruct_3d(temp_path)

        return {
            "status": "success",
            "reconstruction": reconstruction
        }

    except Exception as e:
        import traceback
        print("RECONSTRUCT FACE ERROR:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress/{job_id}", response_model=ProgressResponse)
async def get_progress(job_id: str):
    """
    Progress status endpoint.
    """
    return await orchestrator.get_progress(job_id)


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Health check endpoint.
    """
    return {
        "status": "online",
        "modules": ["GFPGAN", "Real-ESRGAN", "DECA"]
    }
