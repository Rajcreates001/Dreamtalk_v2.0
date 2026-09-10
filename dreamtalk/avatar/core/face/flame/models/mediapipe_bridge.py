# Dreamtalk - 3D Avatar Module
# Extracted from FLAME-Avatar-Driver
# MIT License - Copyright (c) 2025
#
# MediaPipe blendshapes to FLAME coefficient translator.
# Supports both pre-trained linear mappings and manual fallback.

import os
import numpy as np
from typing import Optional, Tuple, List


class MediaPipeToFlame:
    """Convert MediaPipe face blendshape scores to FLAME expression coefficients.

    MediaPipe face blendshapes (52 blendshapes):
        _neutral, browDownLeft, browDownRight, browInnerUp, browOuterUpLeft,
        browOuterUpRight, cheekPuff, cheekSquintLeft, cheekSquintRight,
        eyeBlinkLeft, eyeBlinkRight, eyeLookDownLeft, eyeLookDownRight,
        eyeLookInLeft, eyeLookInRight, eyeLookOutLeft, eyeLookOutRight,
        eyeLookUpLeft, eyeLookUpRight, eyeSquintLeft, eyeSquintRight,
        eyeWideLeft, eyeWideRight, jawForward, jawLeft, jawOpen, jawRight,
        mouthClose, mouthDimpleLeft, mouthDimpleRight, mouthFrownLeft,
        mouthFrownRight, mouthFunnel, mouthLeft, mouthLowerDownLeft,
        mouthLowerDownRight, mouthPressLeft, mouthPressRight, mouthPucker,
        mouthRight, mouthRollLower, mouthRollUpper, mouthShrugLower,
        mouthShrugUpper, mouthSmileLeft, mouthSmileRight, mouthStretchLeft,
        mouthStretchRight, mouthUpperUpLeft, mouthUpperUpRight,
        noseSneerLeft, noseSneerRight
    """

    BLENDSHAPE_NAMES = [
        "_neutral", "browDownLeft", "browDownRight", "browInnerUp",
        "browOuterUpLeft", "browOuterUpRight", "cheekPuff", "cheekSquintLeft",
        "cheekSquintRight", "eyeBlinkLeft", "eyeBlinkRight", "eyeLookDownLeft",
        "eyeLookDownRight", "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft",
        "eyeLookOutRight", "eyeLookUpLeft", "eyeLookUpRight", "eyeSquintLeft",
        "eyeSquintRight", "eyeWideLeft", "eyeWideRight", "jawForward",
        "jawLeft", "jawOpen", "jawRight", "mouthClose", "mouthDimpleLeft",
        "mouthDimpleRight", "mouthFrownLeft", "mouthFrownRight", "mouthFunnel",
        "mouthLeft", "mouthLowerDownLeft", "mouthLowerDownRight", "mouthPressLeft",
        "mouthPressRight", "mouthPucker", "mouthRight", "mouthRollLower",
        "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper", "mouthSmileLeft",
        "mouthSmileRight", "mouthStretchLeft", "mouthStretchRight", "mouthUpperUpLeft",
        "mouthUpperUpRight", "noseSneerLeft", "noseSneerRight",
    ]

    def __init__(
        self,
        mappings_path: str = "./mappings",
        expression_amplification: float = 2.0,
    ):
        """Initialize with optional pre-trained mappings.

        Args:
            mappings_path: Path to folder with bs2exp.npy, bs2pose.npy, bs2eye.npy
            expression_amplification: Multiplier for expression intensity
        """
        self.expression_amplification = expression_amplification
        self.use_pretrained = False
        self.has_pose_mapping = False
        self.has_eye_mapping = False
        self.bs2exp: Optional[np.ndarray] = None
        self.bs2pose: Optional[np.ndarray] = None
        self.bs2eye: Optional[np.ndarray] = None

        self._try_load_mappings(mappings_path)

    def _try_load_mappings(self, mappings_path: str) -> None:
        """Attempt to load pre-trained linear mapping files."""
        possible_paths = [
            mappings_path,
            os.path.abspath(mappings_path),
            "./mappings",
            os.path.join(os.getcwd(), "mappings"),
        ]
        for attempt in possible_paths:
            bs2exp_path = os.path.join(attempt, "bs2exp.npy")
            if os.path.exists(bs2exp_path):
                self.bs2exp = np.load(bs2exp_path)
                self.use_pretrained = True

                bs2pose_path = os.path.join(attempt, "bs2pose.npy")
                if os.path.exists(bs2pose_path):
                    self.bs2pose = np.load(bs2pose_path)
                    self.has_pose_mapping = True
                else:
                    self.bs2pose = np.zeros((52, 3))
                    self.bs2pose[25, 0] = 0.5

                bs2eye_path = os.path.join(attempt, "bs2eye.npy")
                if os.path.exists(bs2eye_path):
                    self.bs2eye = np.load(bs2eye_path)
                    self.has_eye_mapping = True
                else:
                    self.bs2eye = np.zeros((52, 6))
                break

    def mediapipe_scores_to_array(self, mediapipe_scores) -> np.ndarray:
        """Convert MediaPipe blendshape score list to ordered numpy array.

        Args:
            mediapipe_scores: List of MediaPipe Category objects with
                              .category_name and .score attributes

        Returns:
            (52,) numpy array
        """
        score_dict = {b.category_name: b.score for b in mediapipe_scores}
        arr = np.zeros(52)
        for i, name in enumerate(self.BLENDSHAPE_NAMES):
            if name in score_dict:
                arr[i] = score_dict[name]
        return arr

    def translate_pretrained(self, mediapipe_scores) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Convert MediaPipe scores using pre-trained linear mappings.

        Returns:
            (expression, jaw_pose, eye_pose) as numpy arrays
        """
        arr = self.mediapipe_scores_to_array(mediapipe_scores)
        expression = arr @ self.bs2exp
        jaw_pose = arr @ self.bs2pose
        eye_pose = arr @ self.bs2eye
        expression = expression * self.expression_amplification
        return expression, jaw_pose, eye_pose

    def translate_manual(
        self, mediapipe_scores, jaw_mult=8.0, smile_mult=6.0,
        brow_mult=5.0, blink_mult=8.0, funnel_mult=6.0, pucker_mult=6.0
    ) -> np.ndarray:
        """Convert MediaPipe scores using manual fallback mapping.

        Returns:
            expression: (100,) numpy array
        """
        flame_expr = np.zeros(100)
        score_dict = {b.category_name: b.score for b in mediapipe_scores}

        mappings = {
            "jawOpen": (0, jaw_mult),
            "mouthSmileLeft": (1, smile_mult),
            "mouthSmileRight": (2, smile_mult),
            "browInnerUp": (3, brow_mult),
            "eyeBlinkLeft": (4, blink_mult),
            "eyeBlinkRight": (5, blink_mult),
            "mouthFunnel": (6, funnel_mult),
            "mouthPucker": (7, pucker_mult),
        }
        for name, (idx, mult) in mappings.items():
            if name in score_dict:
                flame_expr[idx] = score_dict[name] * mult
        return flame_expr

    def translate(self, mediapipe_scores, return_pose=True):
        """Convert MediaPipe blendshapes to FLAME parameters.

        Args:
            mediapipe_scores: List of MediaPipe blendshape scores
            return_pose: If True and using pre-trained, also return jaw/eye pose

        Returns:
            If pretrained + return_pose: (expression, jaw_pose, eye_pose)
            Otherwise: expression only
        """
        if self.use_pretrained and return_pose:
            return self.translate_pretrained(mediapipe_scores)
        else:
            return self.translate_manual(mediapipe_scores)


class FlameTranslator:
    """High-level translator combining FLAME model + MediaPipe bridge."""

    def __init__(
        self,
        flame_model_path: str,
        mappings_path: str = "./mappings",
        expression_amplification: float = 2.0,
    ):
        from dreamtalk.avatar.core.face.flame.models.flame_model import FLAMEModel
        self.flame = FLAMEModel(flame_model_path)
        self.bridge = MediaPipeToFlame(mappings_path, expression_amplification)
        self.v_template = self.flame.v_template
        self.expression_basis = self.flame.expression_basis

    def translate(self, mediapipe_scores):
        """Convert MediaPipe scores to FLAME parameters.

        Returns:
            If pre-trained mappings available: (expression, jaw_pose, eye_pose)
            Otherwise: expression (or (expression, None, None))
        """
        if self.bridge.use_pretrained:
            return self.bridge.translate_pretrained(mediapipe_scores)
        else:
            expr = self.bridge.translate_manual(mediapipe_scores)
            return expr, None, None

    def deform_mesh(self, flame_expr: np.ndarray, jaw_pose: Optional[np.ndarray] = None) -> np.ndarray:
        """Deform FLAME mesh using expression parameters.

        Args:
            flame_expr: (100,) expression coefficients
            jaw_pose: (3,) optional jaw rotation (not used in simplified deformation)

        Returns:
            (5023, 3) deformed vertices
        """
        return self.flame.deform(flame_expr)

    @property
    def faces(self) -> np.ndarray:
        """Get mesh faces."""
        return self.flame.faces
