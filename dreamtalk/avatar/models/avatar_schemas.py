# Dreamtalk - Avatar Module
# Migrated from Dreamtalk-Avatar-Module

from pydantic import BaseModel
from typing import Optional


class AvatarGenerateResponse(BaseModel):
    status: str
    source_image_url: Optional[str] = None
    video_url: Optional[str] = None
    emotion_used: Optional[str] = None
    intensity: float = 1.0
    mesh_path: Optional[str] = None
    params_path: Optional[str] = None
    message: Optional[str] = None
    last_step: Optional[str] = None


class EnhanceImageResponse(BaseModel):
    status: str
    enhanced_image_path: Optional[str] = None
    enhanced_image_url: Optional[str] = None


class ReconstructFaceResponse(BaseModel):
    status: str
    mesh_path: Optional[str] = None
    params_path: Optional[str] = None


class ProgressResponse(BaseModel):
    job_id: str
    progress: str


class StatusResponse(BaseModel):
    status: str
    modules: list[str]
