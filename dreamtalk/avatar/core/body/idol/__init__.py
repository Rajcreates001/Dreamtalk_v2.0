# Dreamtalk - 3D Avatar Module
# Extracted from IDOL (Single-Image 3D Reconstruction)

from .idol_api import IDOLInference
from .config import IDOLConfig

__all__ = ["IDOLInference", "IDOLConfig"]
