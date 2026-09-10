# Dreamtalk - Voice Engine
# Extracted from Fish Speech

from dataclasses import dataclass
from typing import List, Literal, Optional

import numpy as np
import torch


@dataclass
class BasePart:
    type: Literal["text", "vq", "audio"] | None = None
    cal_loss: bool = False


@dataclass(kw_only=True)
class VQPart(BasePart):
    type = "vq"
    codes: torch.Tensor

    def __post_init__(self):
        self.type = "vq"


@dataclass(kw_only=True)
class TextPart(BasePart):
    type = "text"
    text: str | None = None
    tokens: list[int] | None = None

    def __post_init__(self):
        self.type = "text"
        if self.text is None and self.tokens is None:
            raise ValueError("Either text or tokens must be provided")


@dataclass(kw_only=True)
class AudioPart(BasePart):
    type = "audio"
    features: torch.Tensor

    def __post_init__(self):
        self.type = "audio"
