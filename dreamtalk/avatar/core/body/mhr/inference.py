# Dreamtalk - 3D Avatar Module
# Extracted from MHR
# Copyright (c) Meta Platforms, Inc. and affiliates.
# Licensed under Apache License, Version 2.0
#
# Inference utilities for MHR parametric body model.

import torch
import numpy as np
from typing import Optional, Tuple


def prepare_random_inputs(
    batch_size: int,
    identity_std: float = 0.8,
    model_param_std: float = 0.2,
    face_expr_std: float = 0.3,
    num_identity: int = 45,
    num_model_params: int = 204,
    num_face_expr: int = 72,
    device: torch.device = "cpu",
    seed: Optional[int] = None,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Generate random input parameters for testing.

    Args:
        batch_size: Number of samples
        identity_std: Std for identity coefficients
        model_param_std: Std for model parameters
        face_expr_std: Std for face expression coefficients
        num_identity: Number of identity blendshapes
        num_model_params: Number of model parameters
        num_face_expr: Number of face expression blendshapes
        device: Target device
        seed: Random seed (None = no seed)

    Returns:
        (identity_coeffs, model_parameters, face_expr_coeffs)
    """
    if seed is not None:
        torch.manual_seed(seed)

    identity_coeffs = identity_std * torch.randn(batch_size, num_identity, device=device)
    model_parameters = model_param_std * (torch.rand(batch_size, num_model_params, device=device) - 0.5)
    face_expr_coeffs = face_expr_std * torch.randn(batch_size, num_face_expr, device=device)
    return identity_coeffs, model_parameters, face_expr_coeffs


def export_to_ply(vertices: np.ndarray, faces: np.ndarray, output_path: str) -> None:
    """Export vertex/face mesh to PLY file.

    Args:
        vertices: (N, 3) vertex positions
        faces: (M, 3) triangle indices
        output_path: Output .ply file path
    """
    import trimesh
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.export(output_path)


def export_to_obj(vertices: np.ndarray, faces: np.ndarray, output_path: str) -> None:
    """Export vertex/face mesh to OBJ file.

    Args:
        vertices: (N, 3) vertex positions
        faces: (M, 3) triangle indices
        output_path: Output .obj file path (creates .mtl too if needed)
    """
    import trimesh
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.export(output_path)


def compute_mesh_statistics(vertices: torch.Tensor, faces: torch.Tensor) -> dict:
    """Compute basic mesh statistics.

    Args:
        vertices: (N, 3) vertex positions
        faces: (M, 3) triangle indices

    Returns:
        Dictionary with num_vertices, num_faces, bbox_min, bbox_max, center
    """
    v = vertices.cpu().numpy() if torch.is_tensor(vertices) else vertices
    vmin, vmax = v.min(axis=0), v.max(axis=0)
    return {
        "num_vertices": v.shape[0],
        "num_faces": faces.shape[0] if torch.is_tensor(faces) else faces.shape[0],
        "bbox_min": vmin.tolist(),
        "bbox_max": vmax.tolist(),
        "center": ((vmin + vmax) / 2).tolist(),
    }
