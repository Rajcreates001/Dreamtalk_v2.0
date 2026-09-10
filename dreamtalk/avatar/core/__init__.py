# Dreamtalk - Avatar Module
# Migrated from Dreamtalk-Avatar-Module

from dreamtalk.avatar.core.pipeline import Settings, settings
from dreamtalk.avatar.core.face_swap import FaceReconstructionService
from dreamtalk.avatar.core.animation import EmotionMappingService
from dreamtalk.avatar.core.renderer import ImageProcessingService

__all__ = [
    "Settings",
    "settings",
    "FaceReconstructionService",
    "EmotionMappingService",
    "ImageProcessingService",
]
