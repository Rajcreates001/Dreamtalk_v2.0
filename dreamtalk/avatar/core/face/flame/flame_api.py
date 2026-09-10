# Dreamtalk - 3D Avatar Module
# Extracted from FLAME-Avatar-Driver
# MIT License - Copyright (c) 2025
#
# High-level inference wrapper for real-time face tracking and FLAME animation.

import cv2
import numpy as np
from typing import Optional, Callable

from dreamtalk.avatar.core.face.flame.config import FlameConfig
from dreamtalk.avatar.core.face.flame.models.mediapipe_bridge import FlameTranslator
from dreamtalk.avatar.core.face.flame.inference import (
    get_head_rotation_from_landmarks, build_head_rotation_matrix,
    setup_mediapipe_face_detector, process_video_frames,
)


class FlameAvatarDriver:
    """Real-time face tracking and FLAME avatar animation pipeline.

    Pipeline:
        1. MediaPipe detects facial landmarks + blendshapes
        2. FlameTranslator converts blendshapes to FLAME expression coefficients
        3. FLAME model deforms mesh
        4. Head rotation is applied for full pose
    """

    def __init__(self, config: Optional[FlameConfig] = None):
        self.config = config or FlameConfig()
        self.translator: Optional[FlameTranslator] = None
        self.detector = None
        self._frame_count = 0

    def initialize(self) -> "FlameAvatarDriver":
        """Load models and initialize the pipeline."""
        self.translator = FlameTranslator(
            flame_model_path=self.config.flame_model_path,
            mappings_path=self.config.mappings_path,
            expression_amplification=self.config.expression_amplification,
        )
        self.detector = setup_mediapipe_face_detector(
            self.config.landmarker_model_path
        )
        return self

    def process_frame(self, frame_bgr: np.ndarray, timestamp_ms: int) -> dict:
        """Process a single video frame.

        Args:
            frame_bgr: BGR image from OpenCV
            timestamp_ms: Timestamp in milliseconds

        Returns:
            Dictionary with:
                - "expression": (100,) FLAME expression coefficients
                - "jaw_pose": (3,) jaw rotation or None
                - "eye_pose": (6,) eye rotation or None
                - "deformed_vertices": (5023, 3) or None
                - "yaw": head yaw in radians
                - "pitch": head pitch in radians
                - "has_face": bool
        """
        import mediapipe as mp

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.detector.detect_for_video(mp_image, timestamp_ms)
        self._frame_count += 1

        output = {
            "expression": None,
            "jaw_pose": None,
            "eye_pose": None,
            "deformed_vertices": None,
            "yaw": 0.0,
            "pitch": 0.0,
            "has_face": False,
        }

        if not result.face_blendshapes:
            return output

        # Translate blendshapes to FLAME
        mp_scores = result.face_blendshapes[0]
        translation = self.translator.translate(mp_scores)

        if len(translation) == 3:
            flame_expr, jaw_pose, eye_pose = translation
        else:
            flame_expr = translation
            jaw_pose, eye_pose = None, None

        # Deform mesh
        deformed = self.translator.deform_mesh(flame_expr, jaw_pose)

        # Head rotation
        landmarks = result.face_landmarks[0]
        raw_yaw, raw_pitch = get_head_rotation_from_landmarks(landmarks)
        yaw = -raw_yaw if self.config.invert_yaw else raw_yaw
        pitch = raw_pitch

        R = build_head_rotation_matrix(
            yaw, pitch,
            invert_yaw=self.config.invert_yaw,
            base_z_deg=self.config.base_rotation_z_deg,
            base_x_deg=self.config.base_rotation_x_deg,
        )
        deformed = deformed @ R.T
        deformed -= np.mean(deformed, axis=0)

        output.update({
            "expression": flame_expr,
            "jaw_pose": jaw_pose,
            "eye_pose": eye_pose,
            "deformed_vertices": deformed,
            "yaw": yaw,
            "pitch": pitch,
            "has_face": True,
        })
        return output

    def run_live(
        self,
        video_path: Optional[str] = None,
        on_frame: Optional[Callable] = None,
    ) -> None:
        """Run real-time avatar driving from video or webcam.

        Args:
            video_path: Path to video file (None = use webcam)
            on_frame: Optional callback(frame_bgr, output_dict) for custom rendering.
                      If None, uses built-in display.
        """
        src = video_path or 0
        cap = cv2.VideoCapture(src)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30

        print(f"Starting {'webcam' if video_path is None else video_path} pipeline...")
        print("Press 'q' to quit")

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                timestamp = int(1000 * self._frame_count / fps)
                output = self.process_frame(frame, timestamp)

                if on_frame:
                    on_frame(frame, output)
                else:
                    self._default_display(frame, output)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

    def _default_display(self, frame: np.ndarray, output: dict) -> None:
        """Default frame display with debug info overlay."""
        if output["has_face"]:
            active = np.where(np.abs(output["expression"]) > 0.1)[0]
            info = f"Expr active: {len(active)} | Yaw: {output['yaw']:.2f} | Pitch: {output['pitch']:.2f}"
            cv2.putText(frame, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 0), 2)
        cv2.imshow("Dreamtalk FLAME Avatar Driver", frame)

    @property
    def faces(self) -> np.ndarray:
        """Get mesh faces from FLAME model."""
        return self.translator.flame.faces
