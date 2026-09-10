# Dreamtalk - 3D Avatar Module
# Extracted from MHR
# Copyright (c) Meta Platforms, Inc. and affiliates.
# Licensed under Apache License, Version 2.0
#
# High-level inference wrapper for MHR parametric body model.

import torch
import numpy as np
from pathlib import Path
from typing import Optional, Tuple

from dreamtalk.avatar.core.body.mhr.config import MHRConfig
from dreamtalk.avatar.core.body.mhr.models.body_model import MHRBodyModel
from dreamtalk.avatar.core.body.mhr.models.lod_manager import LODManager
from dreamtalk.avatar.core.body.mhr.inference import prepare_random_inputs, export_to_ply


class MHRInference:
    """High-level wrapper for MHR parametric body model inference."""

    def __init__(self, config: Optional[MHRConfig] = None, device: Optional[torch.device] = None):
        self.config = config or MHRConfig()
        self.device = device or torch.device(self.config.device if torch.cuda.is_available() else "cpu")
        self.model: Optional[MHRBodyModel] = None
        self.lod_manager: Optional[LODManager] = None

    def load_model(self, lod: Optional[int] = None) -> "MHRInference":
        """Load MHR body model at specified LOD level.

        Args:
            lod: LOD level (0-6). If None, uses config.lod.
        """
        if lod is not None:
            self.config.lod = lod

        self.config.device = str(self.device)
        self.model = MHRBodyModel(self.config)
        self.lod_manager = LODManager(Path(self.config.asset_folder))
        return self

    def forward(
        self,
        identity_coeffs: torch.Tensor,
        model_parameters: torch.Tensor,
        face_expr_coeffs: Optional[torch.Tensor] = None,
        apply_correctives: bool = True,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Run body model forward pass.

        Args:
            identity_coeffs: (batch, 45) or (45,) shape coefficients
            model_parameters: (batch, 204) or (204,) pose/rig parameters
            face_expr_coeffs: (batch, 72) or (72,) expression coefficients
            apply_correctives: Apply pose correctives

        Returns:
            (vertices, skeleton_state)
        """
        if self.model is None:
            self.load_model()

        # Handle unbatched inputs
        if identity_coeffs.dim() == 1:
            identity_coeffs = identity_coeffs.unsqueeze(0)
        if model_parameters.dim() == 1:
            model_parameters = model_parameters.unsqueeze(0)
        if face_expr_coeffs is not None and face_expr_coeffs.dim() == 1:
            face_expr_coeffs = face_expr_coeffs.unsqueeze(0)

        identity_coeffs = identity_coeffs.to(self.device)
        model_parameters = model_parameters.to(self.device)
        if face_expr_coeffs is not None:
            face_expr_coeffs = face_expr_coeffs.to(self.device)

        with torch.no_grad():
            verts, skel = self.model(identity_coeffs, model_parameters, face_expr_coeffs, apply_correctives)

        return verts, skel

    def get_default_identity(self) -> torch.Tensor:
        """Get zero identity (mean shape) coefficients."""
        return torch.zeros(1, self.model.get_num_identity_params(), device=self.device)

    def get_default_expression(self) -> torch.Tensor:
        """Get zero expression coefficients."""
        return torch.zeros(1, self.model.get_num_expression_params(), device=self.device)

    def get_default_model_params(self) -> torch.Tensor:
        """Get zero model parameters (T-pose)."""
        return torch.zeros(1, 204, device=self.device)

    def generate_random_mesh(
        self,
        batch_size: int = 1,
        output_path: Optional[str] = None,
        seed: int = 0,
    ) -> Tuple[torch.Tensor, np.ndarray]:
        """Generate a random mesh from the body model.

        Args:
            batch_size: Number of random samples
            output_path: Optional .ply path to save the mesh
            seed: Random seed

        Returns:
            (vertices, faces) for first batch element
        """
        identity, model_params, expr = prepare_random_inputs(
            batch_size, device=self.device, seed=seed
        )
        verts, _ = self.forward(identity, model_params, expr)

        faces = self.model.get_faces()
        if output_path:
            export_to_ply(verts[0].cpu().numpy(), faces, output_path)
        return verts[0].cpu(), faces

    def load_torchscript(self, model_path: str) -> "MHRInference":
        """Load TorchScript-compiled MHR model for deployment."""
        self.model = torch.jit.load(model_path, map_location=self.device)
        self.model.eval()
        return self
