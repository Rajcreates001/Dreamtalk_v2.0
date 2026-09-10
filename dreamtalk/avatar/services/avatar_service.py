# Dreamtalk - Avatar Module
# Migrated from Dreamtalk-Avatar-Module

import os
from urllib.parse import quote

from dreamtalk.avatar.core.renderer import ImageProcessingService
from dreamtalk.avatar.core.face_swap import FaceReconstructionService
from dreamtalk.avatar.core.animation import EmotionMappingService
from dreamtalk.avatar.integrations.did_api import DIDService
from dreamtalk.avatar.core.pipeline import settings


class AvatarService:
    def __init__(self):
        self.image_service = ImageProcessingService()
        self.face_service = FaceReconstructionService()
        self.emotion_service = EmotionMappingService()
        self.did_service = DIDService()

    async def run_full_pipeline(
        self,
        image_path: str,
        text: str,
        emotion: str,
        intensity: float = 1.0
    ):
        results = {"status": "processing", "steps": []}

        try:
            # 1. Enhance uploaded image
            results["steps"].append("Enhancing Image")
            enhanced_path = await self.image_service.enhance_face(image_path)

            # 2. Optional face reconstruction
            results["steps"].append("Creating 3D Face")
            face_3d = await self.face_service.reconstruct_3d(enhanced_path)

            # 3. Convert enhanced image path to public URL
            if not settings.PUBLIC_BASE_URL:
                raise ValueError("PUBLIC_BASE_URL is not configured in .env")

            enhanced_filename = os.path.basename(enhanced_path)

            original_filename = os.path.basename(image_path)

            public_source_url = (
                f"{settings.PUBLIC_BASE_URL}/avatars/{quote(original_filename)}"
            )
            print("D-ID SOURCE URL:", public_source_url)

            # 4. Send public image URL + text to D-ID
            results["steps"].append("Rendering Video")
            video_url = await self.did_service.create_talk(
                source_url=public_source_url,
                text=text,
                emotion=emotion
            )

            return {
                "status": "success",
                "source_image_url": public_source_url,
                "video_url": video_url,
                "emotion_used": emotion,
                "intensity": intensity,
                "3d_face_meta": face_3d,
                "message": "Talking avatar video generated successfully."
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "last_step": results["steps"][-1] if results["steps"] else "initialization"
            }

    async def get_progress(self, job_id: str):
        return {
            "job_id": job_id,
            "progress": "50%"
        }
