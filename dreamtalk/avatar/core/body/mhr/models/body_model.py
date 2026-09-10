# Dreamtalk - 3D Avatar Module
# Extracted from MHR
# Copyright (c) Meta Platforms, Inc. and affiliates.
# Licensed under Apache License, Version 2.0
#
# MHR: Parametric body model with 45 shape + 204 pose + 72 expression parameters.
# Based on pymomentum character model.

import os
import math
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import pymomentum.geometry as pym_geometry
import pymomentum.torch.character as torch_character

from dreamtalk.avatar.core.body.mhr.config import (
    MHRConfig, NUM_IDENTITY_BLENDSHAPES, NUM_FACE_EXPRESSION_BLENDSHAPES, LOD,
)


def batch6DFromXYZ(r, return_9D=False) -> torch.Tensor:
    """Convert XYZ-Euler angles to 6D rotation representation.

    Args:
        r: ... x 3 rotation vectors (Euler XYZ)
        return_9D: If True, return full 3x3 matrix
    Returns:
        ... x 6 (first two columns of rotation matrix) or ... x 3 x 3
    """
    rc = torch.cos(r)
    rs = torch.sin(r)
    cx, cy, cz = rc[..., 0], rc[..., 1], rc[..., 2]
    sx, sy, sz = rs[..., 0], rs[..., 1], rs[..., 2]

    result = torch.stack([
        cy * cz, -cx * sz + sx * sy * cz, sx * sz + cx * sy * cz,
        cy * sz, cx * cz + sx * sy * sz, -sx * cz + cx * sy * sz,
        -sy, sx * cy, cx * cy,
    ], dim=-1).reshape(list(r.shape[:-1]) + [3, 3])

    if not return_9D:
        return torch.cat([result[..., :, 0], result[..., :, 1]], dim=-1)
    return result


class SparseLinear(nn.Module):
    """Sparse linear layer for efficient pose corrective computation."""

    def __init__(self, in_channels, out_channels, sparse_mask, bias=True, load_with_cuda=False):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels

        if not load_with_cuda:
            self.sparse_indices = nn.Parameter(sparse_mask.nonzero().T, requires_grad=False)
        else:
            _sparse_dev = sparse_mask.cuda() if torch.cuda.is_available() else sparse_mask
            self.sparse_indices = nn.Parameter(_sparse_dev.nonzero().T.cpu(), requires_grad=False)
        self.sparse_shape = sparse_mask.shape

        weight = torch.zeros(out_channels, in_channels)
        if bias:
            self.bias = nn.Parameter(torch.zeros(out_channels))
        else:
            self.bias = None

        self.register_buffer("dense_weight", torch.zeros(self.sparse_shape), persistent=False)

        for out_idx in range(out_channels):
            fan_in = sparse_mask[out_idx].sum()
            gain = nn.init.calculate_gain("leaky_relu", math.sqrt(5))
            std = gain / math.sqrt(fan_in)
            bound = math.sqrt(3.0) * std
            weight[out_idx].uniform_(-bound, bound)
            if self.bias is not None:
                self.bias[out_idx:out_idx + 1].uniform_(-1 / math.sqrt(fan_in), 1 / math.sqrt(fan_in))

        self.sparse_weight = nn.Parameter(weight[self.sparse_indices[0], self.sparse_indices[1]])

    def forward(self, x):
        self.dense_weight.zero_()
        self.dense_weight[self.sparse_indices[0], self.sparse_indices[1]] = self.sparse_weight
        if self.bias is None:
            return (self.dense_weight @ x.T).T
        return (self.dense_weight @ x.T).T + self.bias


class MHRPoseCorrectives(nn.Module):
    """Non-linear pose correctives network predicting vertex offsets."""

    def __init__(self, pose_dirs_predictor: nn.Sequential):
        super().__init__()
        self.pose_dirs_predictor = pose_dirs_predictor

    def _pose_features_from_joint_params(self, joint_parameters: torch.Tensor) -> torch.Tensor:
        """Extract 6D rotation features from joint parameters."""
        joint_euler = joint_parameters.reshape(
            joint_parameters.shape[0], -1, pym_geometry.PARAMETERS_PER_JOINT
        )[:, 2:, 3:6]
        joint_6d = batch6DFromXYZ(joint_euler)
        joint_6d[:, :, 0] -= 1
        joint_6d[:, :, 4] -= 1
        return joint_6d.flatten(1, 2)

    def forward(self, joint_parameters: torch.Tensor) -> torch.Tensor:
        """Compute pose corrective vertex offsets.

        Args:
            joint_parameters: (batch, N) local per-joint transforms
        Returns:
            offsets: (batch, num_vertices, 3)
        """
        pose_feats = self._pose_features_from_joint_params(joint_parameters)
        offsets = self.pose_dirs_predictor(pose_feats).reshape(pose_feats.shape[0], -1, 3)
        return offsets


def create_mhr_character(folder: Path, lod: LOD) -> pym_geometry.Character:
    """Load MHR character from FBX and model files.

    Args:
        folder: Asset folder path
        lod: Level of detail (0-6)
    Returns:
        Character with configured blendshape parameter sets
    """
    fbx_path = folder / f"lod{lod}.fbx"
    model_path = folder / "compact_v6_1.model"

    assert os.path.exists(fbx_path), f"MHR FBX not found: {fbx_path}"
    assert os.path.exists(model_path), f"MHR model not found: {model_path}"

    character = pym_geometry.Character.load_fbx(str(fbx_path), str(model_path), load_blendshapes=True)

    n_shapes = character.blend_shape.shape_vectors.shape[0]
    assert n_shapes == NUM_IDENTITY_BLENDSHAPES + NUM_FACE_EXPRESSION_BLENDSHAPES, \
        f"Expected {NUM_IDENTITY_BLENDSHAPES + NUM_FACE_EXPRESSION_BLENDSHAPES} blendshapes, got {n_shapes}"

    n_params = character.parameter_transform.size
    character = character.with_blend_shape(character.blend_shape)
    assert character.parameter_transform.size == n_params + NUM_IDENTITY_BLENDSHAPES + NUM_FACE_EXPRESSION_BLENDSHAPES

    identity_mask = torch.zeros(character.parameter_transform.size, dtype=torch.bool)
    identity_mask[-n_shapes:-n_shapes + NUM_IDENTITY_BLENDSHAPES] = True
    character.parameter_transform.add_parameter_set("identity", identity_mask)

    face_mask = torch.zeros(character.parameter_transform.size, dtype=torch.bool)
    face_mask[-NUM_FACE_EXPRESSION_BLENDSHAPES:] = True
    character.parameter_transform.add_parameter_set("faceExpression", face_mask)

    return character


class MHRBodyModel(nn.Module):
    """MHR parametric body model.

    Parameters:
        - 45 identity (shape) coefficients
        - 204 model parameters (rigid, pose, scale)
        - 72 face expression coefficients
    """

    POSE_CORRECTIVES_SPARSE_MASK_NAME = "posedirs_sparse_mask"
    POSE_CORRECTIVES_COMPONENTS_NAME = "corrective_blendshapes"

    def __init__(self, config: MHRConfig):
        super().__init__()
        self.config = config
        self.folder = Path(config.asset_folder)

        self.character = create_mhr_character(self.folder, config.lod)
        self.character_torch = torch_character.Character(self.character).to(
            torch.device(config.device)
        )

        self.pose_correctives_model = self._build_pose_correctives(config) if config.use_pose_correctives else None

    def _build_pose_correctives(self, config: MHRConfig) -> Optional[MHRPoseCorrectives]:
        """Build pose correctives network from asset files."""
        blendshapes_path = self.folder / f"corrective_blendshapes_lod{config.lod}.npz"
        activation_path = self.folder / "corrective_activation.npz"

        if not os.path.exists(blendshapes_path):
            return None

        blendshapes_data = np.load(blendshapes_path)
        if self.POSE_CORRECTIVES_COMPONENTS_NAME not in blendshapes_data:
            return None
        if not os.path.exists(activation_path):
            return None
        activation_data = np.load(activation_path)

        n_components = blendshapes_data[self.POSE_CORRECTIVES_COMPONENTS_NAME].shape[0]
        n_verts = blendshapes_data[self.POSE_CORRECTIVES_COMPONENTS_NAME].shape[1]

        load_with_cuda = config.device == "cuda" and torch.cuda.is_available()

        state_dict = {
            "0.sparse_indices": torch.from_numpy(activation_data["0.sparse_indices"]),
            "0.sparse_weight": torch.from_numpy(activation_data["0.sparse_weight"]),
            "2.weight": torch.from_numpy(
                blendshapes_data[self.POSE_CORRECTIVES_COMPONENTS_NAME].reshape((n_components, -1)).T
            ),
        }

        sparse_mask = torch.from_numpy(activation_data["posedirs_sparse_mask"])
        posedirs = nn.Sequential(
            SparseLinear(125 * 6, 125 * 24, sparse_mask, bias=False, load_with_cuda=load_with_cuda),
            nn.ReLU(),
            nn.Linear(125 * 24, n_verts * 3, bias=False),
        )
        posedirs.load_state_dict(state_dict)
        for p in posedirs.parameters():
            p.requires_grad = False

        pose_model = MHRPoseCorrectives(posedirs)
        pose_model.to(torch.device(config.device))
        return pose_model

    def forward(
        self,
        identity_coeffs: torch.Tensor,
        model_parameters: torch.Tensor,
        face_expr_coeffs: Optional[torch.Tensor] = None,
        apply_correctives: bool = True,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Compute posed vertices from input parameters.

        Args:
            identity_coeffs: (batch, 45) shape coefficients
            model_parameters: (batch, 204) rigid + pose + scale parameters
            face_expr_coeffs: (batch, 72) expression coefficients, or None (zeros)
            apply_correctives: Apply pose-dependent correctives

        Returns:
            vertices: (batch, num_verts, 3) posed vertex positions
            skel_state: skeleton state
        """
        B = model_parameters.shape[0]
        identity_coeffs = identity_coeffs.expand(B, -1)

        if face_expr_coeffs is None:
            face_expr_coeffs = torch.zeros(B, self.config.num_face_expression_blendshapes,
                                           device=identity_coeffs.device, dtype=identity_coeffs.dtype)

        coeffs = torch.cat([identity_coeffs, face_expr_coeffs], dim=1)

        # Rest pose vertices from blendshapes
        rest_pose = self.character_torch.blend_shape.forward(coeffs)

        # Joint parameters and skeleton state
        model_padding = torch.zeros(B, self.config.num_face_expression_blendshapes +
                                    self.config.num_identity_blendshapes,
                                    device=model_parameters.device, dtype=model_parameters.dtype)
        joint_params = self.character_torch.model_parameters_to_joint_parameters(
            torch.cat([model_parameters, model_padding], dim=1)
        )
        skel_state = self.character_torch.joint_parameters_to_skeleton_state(joint_params)

        # Apply pose correctives
        unposed = rest_pose
        if apply_correctives and self.pose_correctives_model is not None:
            correctives = self.pose_correctives_model(joint_parameters=joint_params)
            unposed = unposed + correctives

        # Skin
        vertices = self.character_torch.skin_points(
            skel_state=skel_state, rest_vertex_positions=unposed
        )
        return vertices, skel_state

    def get_num_identity_params(self) -> int:
        return self.config.num_identity_blendshapes

    def get_num_expression_params(self) -> int:
        return self.config.num_face_expression_blendshapes

    def get_faces(self) -> np.ndarray:
        """Get mesh faces (triangles)."""
        return self.character.mesh.faces
