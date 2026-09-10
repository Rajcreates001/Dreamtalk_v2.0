# Dreamtalk - 3D Avatar Module
# Extracted from MHR
# Copyright (c) Meta Platforms, Inc. and affiliates.
# Licensed under Apache License, Version 2.0

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
import os
import torch


LOD = Literal[0, 1, 2, 3, 4, 5, 6]

NUM_IDENTITY_BLENDSHAPES = 45
NUM_FACE_EXPRESSION_BLENDSHAPES = 72


@dataclass
class MHRConfig:
    """Configuration for MHR parametric body model."""

    # Asset paths
    asset_folder: str = str(Path(__file__).parent.parent.parent / "assets" / "mhr")

    # Device (auto-detect via DREAMTALK_DEVICE env var, CUDA availability, or CPU)
    device: str = os.environ.get("DREAMTALK_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")

    # LOD level (0-6, higher = more detail)
    lod: LOD = 1

    # Pose correctives
    use_pose_correctives: bool = True

    # Model parameters
    num_identity_blendshapes: int = NUM_IDENTITY_BLENDSHAPES
    num_face_expression_blendshapes: int = NUM_FACE_EXPRESSION_BLENDSHAPES

    # Default coefficients
    identity_std: float = 0.8
    model_param_std: float = 0.2
    face_expr_std: float = 0.3

    # TorchScript
    torchscript_path: str = ""
    use_torchscript: bool = False
