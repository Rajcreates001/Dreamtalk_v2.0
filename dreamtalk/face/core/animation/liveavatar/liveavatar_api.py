# Dreamtalk - Face Engine
# Extracted from LiveAvatar
import torch
from .config import LiveAvatarConfig


class LiveAvatarAPI:
    def __init__(self, config: LiveAvatarConfig = None):
        self.config = config or LiveAvatarConfig()

    def load_models(self):
        pass

    def generate(self, audio_path, source_image_path, output_path):
        raise NotImplementedError("LiveAvatar inference requires full model implementation")
