# Dreamtalk - Voice Engine
# Extracted from ChatTTS (simplified, no numba dependency)

import json
import logging
import re
from typing import Dict, List, Literal, Optional

import numpy as np


class Normalizer:
    def __init__(self, map_path: str, logger=logging.getLogger(__name__)):
        self.logger = logger
        self.homophones = {}
        if map_path and os.path.exists(map_path):
            with open(map_path, "r", encoding="utf-8") as f:
                self.homophones = json.load(f)

    def destroy(self):
        self.homophones.clear()

    def __call__(
        self,
        text: str,
        do_text_normalization=True,
        do_homophone_replacement=True,
        lang: Optional[str] = None,
    ) -> str:
        if not do_text_normalization and not do_homophone_replacement:
            return text
        if do_homophone_replacement and self.homophones:
            for wrong, correct in self.homophones.items():
                text = text.replace(wrong, correct)
        return text


import os
