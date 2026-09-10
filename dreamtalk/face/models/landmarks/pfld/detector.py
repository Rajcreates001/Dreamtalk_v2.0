"""PFLD Face Landmark Detector — wrapper for PFLDModel with image preprocessing."""

import cv2
import numpy as np
import torch
import logging
from typing import Optional, List, Tuple

from .model import PFLDModel, create_pfld_model

logger = logging.getLogger("dreamtalk.face.landmarks.pfld")


class PFLDFaceDetection:
    """PFLD face landmark detector.

    Detects 106 facial landmarks from face images using the PFLD model.
    Handles image preprocessing (grayscale, resize, normalization).
    """

    def __init__(self, weight_path: Optional[str] = None, device: str = "cpu"):
        self.device = device
        self.num_landmarks = 106
        self.img_size = (112, 96)  # H, W (PFLD standard)

        if weight_path and not weight_path.endswith(".pth"):
            weight_path = None  # Let it be loaded lazily

        self.model: Optional[PFLDModel] = None
        if weight_path:
            self.load_model(weight_path)

    def load_model(self, weight_path: str):
        """Load PFLD weights into the model."""
        try:
            self.model = create_pfld_model(weight_path, self.device, self.num_landmarks)
            logger.info("PFLD model loaded from %s", weight_path)
        except Exception as e:
            logger.warning("Failed to load PFLD from %s: %s", weight_path, e)
            self.model = None

    @staticmethod
    def _preprocess_image(img: np.ndarray) -> torch.Tensor:
        """Preprocess a face image for PFLD inference.

        Args:
            img: BGR or grayscale image (H, W, 3) or (H, W)

        Returns:
            tensor: (1, 1, 112, 96) normalized to [0, 1]
        """
        if img is None or img.size == 0:
            raise ValueError("Empty image")

        # Convert to grayscale if needed
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # Resize to PFLD input size
        resized = cv2.resize(gray, (96, 112), interpolation=cv2.INTER_LINEAR)

        # Normalize to [0, 1]
        normalized = resized.astype(np.float32) / 255.0

        # Add batch and channel dimensions: (1, 1, 112, 96)
        tensor = torch.from_numpy(normalized).unsqueeze(0).unsqueeze(0)

        return tensor

    def predict_landmarks(
        self, img: np.ndarray, return_raw: bool = False,
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Detect 106 facial landmarks from a face image.

        Args:
            img: BGR face image (H, W, 3)
            return_raw: If True, return raw [0,1] normalized landmarks

        Returns:
            (landmarks, raw_landmarks):
                landmarks: (106, 2) in image coordinates (pixels)
                raw_landmarks: (106, 2) in [0,1] normalized (or None if return_raw=False)
        """
        if self.model is None:
            raise RuntimeError("PFLD model not loaded. Call load_model() first.")

        h, w = img.shape[:2]

        # Preprocess
        tensor = self._preprocess_image(img).to(self.device)

        # Inference
        with torch.no_grad():
            raw = self.model.predict(tensor)

        # Convert to numpy
        raw_np = raw.squeeze(0).cpu().numpy()  # (106, 2)

        # Scale from [0,1] to image coordinates
        landmarks = raw_np.copy()
        landmarks[:, 0] *= w
        landmarks[:, 1] *= h

        if return_raw:
            return landmarks, raw_np
        return landmarks, None

    def extract_landmarks_from_face(
        self, face_img: np.ndarray, normalize: bool = True,
    ) -> List[List[float]]:
        """Convenience method returning landmarks as list of [x, y].

        Args:
            face_img: Cropped face BGR image
            normalize: If True, normalize landmarks to [0,1] relative to face crop

        Returns:
            List of [x, y] landmark coordinates
        """
        landmarks, raw = self.predict_landmarks(face_img, return_raw=normalize)
        if normalize and raw is not None:
            return raw.tolist()
        return landmarks.tolist()

    def draw_landmarks(self, img: np.ndarray, landmarks: np.ndarray, color=(0, 255, 0), radius: int = 1) -> np.ndarray:
        """Draw landmarks on image for visualization.

        Args:
            img: Image to draw on
            landmarks: (N, 2) array of landmark coordinates
            color: BGR color tuple
            radius: Circle radius

        Returns:
            Image with landmarks drawn
        """
        vis = img.copy()
        for (x, y) in landmarks.astype(int):
            cv2.circle(vis, (x, y), radius, color, -1)
        return vis


def detect_landmarks(
    face_image: np.ndarray,
    detector: PFLDFaceDetection,
) -> Optional[List[List[float]]]:
    """Utility function for quick landmark detection.

    Args:
        face_image: Cropped face BGR image
        detector: Initialized PFLDFaceDetection instance

    Returns:
        List of (106) [x, y] landmarks or None on failure
    """
    try:
        landmarks, _ = detector.predict_landmarks(face_image, return_raw=True)
        return landmarks.tolist()
    except Exception as e:
        logger.error("PFLD landmark detection failed: %s", e)
        return None
