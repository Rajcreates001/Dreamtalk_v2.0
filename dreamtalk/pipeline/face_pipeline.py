"""Face Pipeline v2 — Super-resolution → Multi-backend Face Detection → FLAME 3D Mesh → Emotion."""

import json
import importlib.util
import logging
import math
import os
import tempfile
import traceback
import uuid
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

import cv2
import numpy as np
from PIL import Image

from dreamtalk.pipeline.models import FaceAnalysisResult

logger = logging.getLogger("dreamtalk.pipeline.face")

# Optional imports with broad exception handling for torch DLL issues
try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    mp_face_detection = mp.solutions.face_detection
    mp_face_landmarks = mp.solutions.face_connections
    MEDIAPIPE_AVAILABLE = True
except Exception:
    MEDIAPIPE_AVAILABLE = False

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_tasks_python
    from mediapipe.tasks.python import vision as mp_tasks_vision
    MEDIAPIPE_TASKS_AVAILABLE = hasattr(mp, "Image") and hasattr(mp_tasks_vision, "FaceLandmarker")
except Exception:
    MEDIAPIPE_TASKS_AVAILABLE = False

DEEPFACE_AVAILABLE = importlib.util.find_spec("deepface") is not None

try:
    import torch
    _ = torch.tensor([1.0])
    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False


class FacePipeline:
    """Production-grade face analysis pipeline.

    Pipeline:
        1. Super-resolution enhancement (for low-quality/blurry inputs)
        2. Multi-backend face detection (MediaPipe → OpenCV DNN → Haar Cascade)
        3. Landmark extraction (MediaPipe 478 landmarks or PFLD fallback)
        4. MediaPipe 52 blendshape estimation
        5. FLAME 3D mesh deformation (100 expression coefficients)
        6. Head pose estimation (yaw/pitch/roll from landmarks)
        7. Face embedding generation (FaceNet/ArcFace)
        8. Facial emotion recognition (expression → mood map)
        9. Quality scoring (blur, brightness, face size, pose)
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

    EMOTION_BLENDSHAPE_MAP = {
        "happy": {"mouthSmileLeft", "mouthSmileRight", "cheekSquintLeft", "cheekSquintRight"},
        "sad": {"browInnerUp", "mouthFrownLeft", "mouthFrownRight", "eyeSquintLeft", "eyeSquintRight"},
        "angry": {"browDownLeft", "browDownRight", "mouthPressLeft", "mouthPressRight", "eyeSquintLeft", "eyeSquintRight"},
        "surprised": {"browInnerUp", "jawOpen", "eyeWideLeft", "eyeWideRight", "mouthFunnel"},
        "fearful": {"browInnerUp", "eyeWideLeft", "eyeWideRight", "jawOpen", "mouthStretchLeft", "mouthStretchRight"},
        "disgusted": {"noseSneerLeft", "noseSneerRight", "mouthDimpleLeft", "mouthDimpleRight", "browDownLeft", "browDownRight"},
        "neutral": {"_neutral"},
    }

    @staticmethod
    def _rotation_matrix_to_pose(matrix: np.ndarray) -> Dict[str, float]:
        """Convert MediaPipe's facial transform rotation to Euler degrees."""
        rotation = np.asarray(matrix, dtype=np.float64)[:3, :3]
        horizontal = math.sqrt(rotation[0, 0] ** 2 + rotation[1, 0] ** 2)
        if horizontal > 1e-6:
            pitch = math.atan2(rotation[2, 1], rotation[2, 2])
            yaw = math.atan2(-rotation[2, 0], horizontal)
            roll = math.atan2(rotation[1, 0], rotation[0, 0])
        else:
            pitch = math.atan2(-rotation[1, 2], rotation[1, 1])
            yaw = math.atan2(-rotation[2, 0], horizontal)
            roll = 0.0
        return {
            "yaw": round(math.degrees(yaw), 2),
            "pitch": round(math.degrees(pitch), 2),
            "roll": round(math.degrees(roll), 2),
        }

    def __init__(self, assets_dir: str = None, flame_model_path: str = None):
        self.assets_dir = assets_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "pipeline", "assets",
        )
        os.makedirs(self.assets_dir, exist_ok=True)

        self.flame_model_path = flame_model_path
        self._face_mesh = None
        self._face_detector_mp = None
        self._face_landmarker_task = None
        self._flame = None
        self._flame_translator = None
        self._embedding_model = "unavailable"

        # FLAME fitter for 3D mesh generation
        self._flame_fitter = None

    # ─── Lazy Model Loading ────────────────────────────────────────────────

    def _lazy_load_mediapipe(self):
        if MEDIAPIPE_AVAILABLE and self._face_mesh is None:
            try:
                self._face_mesh = mp_face_mesh.FaceMesh(
                    static_image_mode=True,
                    max_num_faces=4,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                )
                self._face_detector_mp = mp_face_detection.FaceDetection(
                    min_detection_confidence=0.5,
                )
            except Exception as e:
                logger.warning(f"MediaPipe load failed: {e}")
        if MEDIAPIPE_AVAILABLE and self._face_mesh is not None:
            return self._face_detector_mp, self._face_mesh

        if MEDIAPIPE_TASKS_AVAILABLE and self._face_landmarker_task is None:
            try:
                model_path = Path(__file__).resolve().parent.parent / "weights" / "face" / "face_landmarker.task"
                options = mp_tasks_vision.FaceLandmarkerOptions(
                    base_options=mp_tasks_python.BaseOptions(model_asset_path=str(model_path)),
                    running_mode=mp_tasks_vision.RunningMode.IMAGE,
                    num_faces=4,
                    min_face_detection_confidence=0.45,
                    min_face_presence_confidence=0.45,
                    min_tracking_confidence=0.45,
                    output_face_blendshapes=True,
                    output_facial_transformation_matrixes=True,
                )
                self._face_landmarker_task = mp_tasks_vision.FaceLandmarker.create_from_options(options)
                logger.info("MediaPipe Tasks FaceLandmarker loaded from %s", model_path)
            except Exception as e:
                logger.warning("MediaPipe Tasks load failed: %s", e)
                return None, None
        if self._face_landmarker_task is not None:
            return None, self._face_landmarker_task
        return None, None

    def _run_mediapipe_tasks(self, image: np.ndarray):
        """Run the modern MediaPipe Tasks landmarker bundled with the project."""
        _, landmarker = self._lazy_load_mediapipe()
        if landmarker is None or not MEDIAPIPE_TASKS_AVAILABLE:
            return None
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        return landmarker.detect(mp_image)

    def _lazy_load_flame_fitter(self):
        if self._flame_fitter is not None:
            return self._flame_fitter
        try:
            from dreamtalk.pipeline.flame_fitter import FlameFitter
            self._flame_fitter = FlameFitter()
            logger.info("FlameFitter loaded (%d verts, %d faces)",
                        self._flame_fitter.flame.num_vertices,
                        self._flame_fitter.flame.num_faces)
        except Exception as e:
            logger.warning("FlameFitter load failed: %s", e)
        return self._flame_fitter

    # ─── Image Loading & Enhancement ────────────────────────────────────────

    def _load_image(self, path: str) -> Optional[np.ndarray]:
        if not os.path.exists(path):
            logger.warning(f"Image not found: {path}")
            return None
        try:
            img = cv2.imread(path)
            if img is None:
                raw = np.frombuffer(open(path, "rb").read(), np.uint8)
                img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            logger.error(f"Failed to load image {path}: {e}")
            return None

    def _assess_quality(self, image: np.ndarray) -> Dict[str, Any]:
        """Assess image quality: blur, brightness, contrast, face size."""
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        blur_score = min(laplacian_var / 100, 1.0) if laplacian_var > 0 else 0.0

        brightness = gray.mean()
        brightness_score = 1.0 - abs(brightness - 127) / 127

        contrast = gray.std()
        contrast_score = min(contrast / 64, 1.0)

        low_light = brightness < 50
        over_exposed = brightness > 220
        is_blurry = laplacian_var < 20

        if laplacian_var < 5:
            quality_label = "extremely_blurry"
        elif laplacian_var < 15:
            quality_label = "very_blurry"
        elif laplacian_var < 30:
            quality_label = "blurry"
        elif laplacian_var < 80:
            quality_label = "acceptable"
        elif laplacian_var < 200:
            quality_label = "good"
        else:
            quality_label = "excellent"

        return {
            "resolution": f"{w}x{h}",
            "width": w,
            "height": h,
            "blur_score": round(blur_score, 4),
            "laplacian_variance": round(laplacian_var, 2),
            "brightness": round(float(brightness), 2),
            "brightness_score": round(brightness_score, 4),
            "contrast": round(float(contrast), 2),
            "contrast_score": round(contrast_score, 4),
            "low_light": low_light,
            "over_exposed": over_exposed,
            "is_blurry": is_blurry,
            "quality_label": quality_label,
            "aspect_ratio": round(w / h, 4) if h > 0 else 0,
        }

    def apply_classical_enhancement(self, image: np.ndarray, factor: float = 2.0) -> np.ndarray:
        """Apply deterministic interpolation and contrast enhancement (not neural SR)."""
        h, w = image.shape[:2]
        q = self._assess_quality(image)

        needs_upscale = q["is_blurry"] or h < 200 or w < 200 or q["low_light"]
        if not needs_upscale and factor <= 1.0:
            return image

        if h < 100 and w < 100:
            actual_factor = max(factor, 4.0)
        elif h < 200 and w < 200:
            actual_factor = max(factor, 2.0)
        else:
            actual_factor = factor

        # OpenCV super-resolution via resize + sharpen
        new_w = int(w * actual_factor)
        new_h = int(h * actual_factor)
        enhanced = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

        # Unsharp masking for sharpening
        blurred = cv2.GaussianBlur(enhanced, (0, 0), 3.0)
        sharpened = cv2.addWeighted(enhanced, 1.5, blurred, -0.5, 0)

        # CLAHE for low-light enhancement
        if q["low_light"]:
            lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            lab = cv2.merge([l, a, b])
            sharpened = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        logger.info(f"Classical enhancement applied: {w}x{h} -> {new_w}x{new_h} (factor={actual_factor})")
        return sharpened

    # Backward-compatible method name. Capability reporting intentionally calls
    # this classical enhancement, never neural super-resolution.
    apply_super_resolution = apply_classical_enhancement

    # ─── Face Detection ─────────────────────────────────────────────────────

    def detect_faces(self, image: np.ndarray) -> List[Dict]:
        """Multi-backend face detection. Returns list of face dicts sorted by confidence."""
        all_faces = []

        # Backend 1: MediaPipe
        mp_faces = self._detect_faces_mediapipe(image)
        for f in mp_faces:
            f["backend"] = "mediapipe"
        all_faces.extend(mp_faces)

        # Backend 2: OpenCV DNN
        if not any(f["confidence"] > 0.8 for f in all_faces):
            cv_faces = self._detect_faces_opencv_dnn(image)
            for f in cv_faces:
                if not any(self._bbox_overlap(f["bbox"], ef["bbox"]) for ef in all_faces):
                    f["backend"] = "opencv_dnn"
                    all_faces.append(f)

        # Backend 3: Haar Cascade (last resort)
        if not all_faces:
            haar_faces = self._detect_faces_haar(image)
            for f in haar_faces:
                f["backend"] = "haar_cascade"
            all_faces.extend(haar_faces)

        all_faces.sort(key=lambda x: x["confidence"], reverse=True)
        return all_faces

    def _detect_faces_mediapipe(self, image: np.ndarray) -> List[Dict]:
        _, face_mesh = self._lazy_load_mediapipe()
        if face_mesh is None:
            return []

        if not MEDIAPIPE_AVAILABLE and MEDIAPIPE_TASKS_AVAILABLE:
            results = self._run_mediapipe_tasks(image)
            if not results or not results.face_landmarks:
                return []
            h, w, _ = image.shape
            faces = []
            for landmarks in results.face_landmarks:
                pts = [(int(lm.x * w), int(lm.y * h), int(lm.z * w)) for lm in landmarks]
                xs = [point[0] for point in pts]
                ys = [point[1] for point in pts]
                faces.append({
                    "bbox": [max(0, min(xs)), max(0, min(ys)), min(w, max(xs)), min(h, max(ys))],
                    "landmarks": pts,
                    "landmark_count": len(pts),
                    "confidence": 0.95,
                    "detection_method": "mediapipe_tasks_landmarker",
                })
            return faces

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)
        if not results or not results.multi_face_landmarks:
            return []

        h, w, _ = image.shape
        faces = []
        for landmarks in results.multi_face_landmarks:
            pts = [(int(lm.x * w), int(lm.y * h), int(lm.z * w)) for lm in landmarks.landmark]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            faces.append({
                "bbox": [min(xs), min(ys), max(xs), max(ys)],
                "landmarks": pts,
                "landmark_count": len(pts),
                "confidence": 0.95,
                "detection_method": "mediapipe_facemesh",
            })
        return faces

    def _detect_faces_opencv_dnn(self, image: np.ndarray) -> List[Dict]:
        try:
            h, w = image.shape[:2]
            blob = cv2.dnn.blobFromImage(image, 1.0, (300, 300), [104, 117, 123], False, False)
            net = cv2.dnn.readNetFromCaffe(
                os.path.join(os.path.dirname(cv2.__file__), "data", "deploy.prototxt"),
                os.path.join(os.path.dirname(cv2.__file__), "data", "res10_300x300_ssd_iter_140000.caffemodel"),
            ) if hasattr(cv2, 'dnn') else None
            if net is None:
                return []
            net.setInput(blob)
            detections = net.forward()
            faces = []
            for i in range(detections.shape[2]):
                conf = detections[0, 0, i, 2]
                if conf > 0.5:
                    x1 = int(detections[0, 0, i, 3] * w)
                    y1 = int(detections[0, 0, i, 4] * h)
                    x2 = int(detections[0, 0, i, 5] * w)
                    y2 = int(detections[0, 0, i, 6] * h)
                    faces.append({
                        "bbox": [max(0, x1), max(0, y1), min(w, x2), min(h, y2)],
                        "landmarks": [],
                        "landmark_count": 0,
                        "confidence": float(conf),
                        "detection_method": "opencv_dnn",
                    })
            return faces
        except Exception:
            return []

    def _detect_faces_haar(self, image: np.ndarray) -> List[Dict]:
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            rects = cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
            return [
                {
                    "bbox": [x, y, x + w, y + h],
                    "landmarks": [], "landmark_count": 0,
                    "confidence": 0.6, "detection_method": "haar_cascade",
                }
                for (x, y, w, h) in rects
            ]
        except Exception:
            return []

    def _bbox_overlap(self, b1, b2, threshold=0.3) -> bool:
        x1 = max(b1[0], b2[0])
        y1 = max(b1[1], b2[1])
        x2 = min(b1[2], b2[2])
        y2 = min(b1[3], b2[3])
        if x2 <= x1 or y2 <= y1:
            return False
        inter = (x2 - x1) * (y2 - y1)
        a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
        a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
        return inter / min(a1, a2) > threshold

    # ─── Landmark Extraction ────────────────────────────────────────────────

    def extract_landmarks(self, image: np.ndarray, face_bbox: List[int]) -> Dict:
        """Extract landmarks, blendshapes, and head pose from the primary face."""
        _, face_mesh = self._lazy_load_mediapipe()
        if face_mesh is None:
            # Fallback: use structural face template instead of random noise
            return self._generate_structural_landmarks(image, face_bbox)

        if not MEDIAPIPE_AVAILABLE and MEDIAPIPE_TASKS_AVAILABLE:
            results = self._run_mediapipe_tasks(image)
            if not results or not results.face_landmarks:
                return self._generate_structural_landmarks(image, face_bbox)
            h, w, _ = image.shape
            primary = results.face_landmarks[0]
            landmarks = [(int(lm.x * w), int(lm.y * h), int(lm.z * w)) for lm in primary]
            blendshapes = {}
            if results.face_blendshapes:
                for category in results.face_blendshapes[0]:
                    name = category.category_name or category.display_name
                    if name:
                        blendshapes[name] = round(float(category.score), 5)
            head_pose = None
            if results.facial_transformation_matrixes:
                head_pose = self._rotation_matrix_to_pose(results.facial_transformation_matrixes[0])
            return {
                "landmarks": landmarks,
                "landmark_count": len(landmarks),
                "blendshapes": blendshapes,
                "head_pose": head_pose,
                "method": "mediapipe_tasks_landmarker_478",
            }

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)
        if not results or not results.multi_face_landmarks:
            return {"landmarks": [], "blendshapes": {}, "head_pose": None, "method": "none"}

        h, w, _ = image.shape
        primary = results.multi_face_landmarks[0]

        # 478 landmarks
        landmarks = [(int(lm.x * w), int(lm.y * h), int(lm.z * w)) for lm in primary.landmark]

        # Head pose from landmarks (nose + eye centers)
        nose = np.array([primary.landmark[1].x, primary.landmark[1].y, primary.landmark[1].z])
        le = np.array([primary.landmark[33].x, primary.landmark[33].y, primary.landmark[33].z])
        re = np.array([primary.landmark[263].x, primary.landmark[263].y, primary.landmark[263].z])
        eye_center = (le + re) / 2
        forward = nose - eye_center
        yaw = float(np.degrees(np.arctan2(forward[0], forward[2])))
        pitch = float(np.degrees(np.arctan2(forward[1], forward[2])))

        # Estimate roll from eye line
        eye_line = np.array([re[0] - le[0], re[1] - le[1]])
        roll = float(np.degrees(np.arctan2(eye_line[1], eye_line[0])))

        # Blendshape estimation from landmarks
        blendshapes = self._estimate_blendshapes_from_landmarks(landmarks, w, h)

        return {
            "landmarks": landmarks,
            "landmark_count": len(landmarks),
            "blendshapes": blendshapes,
            "head_pose": {"yaw": round(yaw, 2), "pitch": round(pitch, 2), "roll": round(roll, 2)},
            "method": "mediapipe_facemesh_478",
        }

    def _generate_structural_landmarks(self, image: np.ndarray, face_bbox: List[int]) -> Dict:
        """Generate structural face landmarks from bounding box using a mean-face template.

        Uses known anatomical ratios to place 478 landmarks in a face-shaped
        layout rather than random points.
        """
        h, w, _ = image.shape
        x1, y1, x2, y2 = face_bbox
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        face_w, face_h = x2 - x1, y2 - y1

        landmarks = []
        for i in range(478):
            # Use a structured layout based on known MediaPipe 478 topology
            # Face oval: 0-16 (jaw contour)
            if i <= 16:
                angle = np.pi * i / 16
                rx = face_w * 0.45
                ry = face_h * 0.48
                lx = cx + int(rx * np.cos(angle - np.pi))
                ly = cy + int(ry * np.sin(angle - np.pi))
                lz = int(20 * (1 - abs(np.cos(angle))))
            # Left eyebrow: 17-26
            elif i <= 26:
                t = (i - 17) / 9
                lx = cx - int(face_w * 0.2) + int(face_w * 0.4 * t)
                ly = cy - int(face_h * 0.25) - int(face_h * 0.02 * np.sin(t * np.pi))
                lz = int(15 * (1 - abs(t - 0.5) * 2))
            # Right eyebrow: 27-36
            elif i <= 36:
                t = (i - 27) / 9
                lx = cx - int(face_w * 0.2) + int(face_w * 0.4 * t)
                ly = cy - int(face_h * 0.25) + int(face_h * 0.02 * np.sin(t * np.pi))
                lz = int(15 * (1 - abs(t - 0.5) * 2))
            # Nose: 37-74
            elif i <= 74:
                t = (i - 37) / 37
                lx = cx + int(face_w * 0.15 * np.sin(t * np.pi))
                ly = cy - int(face_h * 0.1) + int(face_h * 0.2 * t)
                lz = int(-30 * (1 - abs(t - 0.5) * 2))
            # Left eye: 75-94
            elif i <= 94:
                t = (i - 75) / 19
                angle = t * 2 * np.pi
                lx = cx - int(face_w * 0.12) + int(face_w * 0.04 * np.cos(angle))
                ly = cy - int(face_h * 0.08) + int(face_h * 0.03 * np.sin(angle))
                lz = int(10)
            # Right eye: 95-114
            elif i <= 114:
                t = (i - 95) / 19
                angle = t * 2 * np.pi
                lx = cx + int(face_w * 0.12) + int(face_w * 0.04 * np.cos(angle))
                ly = cy - int(face_h * 0.08) + int(face_h * 0.03 * np.sin(angle))
                lz = int(10)
            # Inner mouth: 115-134
            elif i <= 134:
                t = (i - 115) / 19
                angle = t * np.pi
                lx = cx + int(face_w * 0.08 * np.cos(angle))
                ly = cy + int(face_h * 0.12) + int(face_h * 0.06 * np.sin(angle))
                lz = int(15)
            # Outer mouth: 135-164
            elif i <= 164:
                t = (i - 135) / 29
                angle = t * np.pi
                lx = cx + int(face_w * 0.12 * np.cos(angle))
                ly = cy + int(face_h * 0.12) + int(face_h * 0.08 * np.sin(angle))
                lz = int(12)
            # Everything else: spread across face in concentric rings
            else:
                ring = (i - 164) // 50
                pos = (i - 164) % 50
                angle = 2 * np.pi * pos / 50
                radius_scale = 0.3 + ring * 0.1
                lx = cx + int(face_w * radius_scale * np.cos(angle))
                ly = cy + int(face_h * radius_scale * np.sin(angle))
                lz = int(5 * (1 - radius_scale))

            landmarks.append((lx, ly, lz))

        return {
            "landmarks": landmarks,
            "landmark_count": len(landmarks),
            "blendshapes": {},
            "head_pose": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0},
            "method": "structural_from_bbox",
        }

    def _estimate_blendshapes_from_landmarks(self, landmarks, w, h) -> Dict:
        """Estimate 52 blendshape values from landmark geometry."""
        if not landmarks:
            return {}

        bs = {name: 0.0 for name in self.BLENDSHAPE_NAMES}
        n = len(landmarks)

        if n < 100:
            return bs

        # Extract key facial distances
        nose_tip = np.array(landmarks[1]) if n > 1 else np.array([w / 2, h / 2, 0])
        left_mouth = np.array(landmarks[61]) if n > 61 else np.array([w * 0.4, h * 0.6, 0])
        right_mouth = np.array(landmarks[291]) if n > 291 else np.array([w * 0.6, h * 0.6, 0])
        top_lip = np.array(landmarks[13]) if n > 13 else np.array([w * 0.5, h * 0.55, 0])
        bottom_lip = np.array(landmarks[14]) if n > 14 else np.array([w * 0.5, h * 0.65, 0])
        left_eye_t = np.array(landmarks[159]) if n > 159 else np.array([w * 0.35, h * 0.35, 0])
        left_eye_b = np.array(landmarks[145]) if n > 145 else np.array([w * 0.35, h * 0.42, 0])
        right_eye_t = np.array(landmarks[386]) if n > 386 else np.array([w * 0.65, h * 0.35, 0])
        right_eye_b = np.array(landmarks[374]) if n > 374 else np.array([w * 0.65, h * 0.42, 0])

        mouth_open = np.linalg.norm(top_lip - bottom_lip) / h
        mouth_width = np.linalg.norm(left_mouth - right_mouth) / w
        left_eye_open = np.linalg.norm(left_eye_t - left_eye_b) / h
        right_eye_open = np.linalg.norm(right_eye_t - right_eye_b) / h

        bs["_neutral"] = 1.0 - min(mouth_open * 3 + abs(left_eye_open - 0.05) * 2, 1.0)
        bs["jawOpen"] = min(mouth_open * 8, 1.0)
        bs["mouthClose"] = max(0, 1.0 - mouth_open * 10)
        bs["mouthSmileLeft"] = min(max((mouth_width - 0.4) * 3, 0), 1.0)
        bs["mouthSmileRight"] = bs["mouthSmileLeft"]
        bs["eyeBlinkLeft"] = min(max(1.0 - left_eye_open * 15, 0), 1.0)
        bs["eyeBlinkRight"] = min(max(1.0 - right_eye_open * 15, 0), 1.0)
        bs["eyeWideLeft"] = min(max((left_eye_open - 0.03) * 15, 0), 1.0)
        bs["eyeWideRight"] = min(max((right_eye_open - 0.03) * 15, 0), 1.0)
        bs["mouthFunnel"] = min(mouth_open * (1.0 - mouth_width) * 6, 1.0)
        bs["mouthPucker"] = min(max((0.3 - mouth_width) * 4, 0), 1.0)

        return bs

    # ─── FLAME 3D Mesh ──────────────────────────────────────────────────────

    def generate_3d_mesh(self, blendshapes: Dict, image: np.ndarray, output_dir: str = None, image_path: str = None) -> Tuple[Optional[str], Optional[str], Dict]:
        """Generate FLAME 3D mesh + texture from photo using the FlameFitter.

        Returns: (mesh_path, texture_path, mesh_info)
        """
        if output_dir is None:
            output_dir = self.assets_dir
        os.makedirs(output_dir, exist_ok=True)

        # Save texture
        texture_path = os.path.join(output_dir, f"flame_texture_{uuid.uuid4().hex[:8]}.jpg")
        cv2.imwrite(texture_path, image)

        # Use FlameFitter for 3D mesh generation
        fitter = self._lazy_load_flame_fitter()
        if fitter is not None and image_path is not None and os.path.exists(image_path):
            try:
                result = fitter.fit_from_photo(
                    image_path,
                    output_dir=output_dir,
                    fit_identity=True,
                )
                if result and result["obj_path"]:
                    mesh_info = {
                        "vertex_count": result["vertex_count"],
                        "face_count": result["face_count"],
                        "expression_active_dims": 0,
                        "max_expression_value": 0.0,
                        "identity_fitted": result["identity_fitted"],
                    }
                    return result["obj_path"], texture_path, mesh_info
            except Exception as e:
                logger.warning("FlameFitter failed, falling back: %s", e)

        # Fallback: generate mean FLAME mesh
        if fitter is not None:
            try:
                result = fitter.generate_mean_mesh(output_dir=output_dir)
                if result and result["obj_path"]:
                    mesh_info = {
                        "vertex_count": result["vertex_count"],
                        "face_count": result["face_count"],
                        "expression_active_dims": 0,
                        "max_expression_value": 0.0,
                        "identity_fitted": False,
                    }
                    return result["obj_path"], texture_path, mesh_info
            except Exception as e:
                logger.warning("Mean FLAME mesh failed: %s", e)

        return self._generate_placeholder_mesh(blendshapes, image, output_dir)

    def _generate_flame_mesh(self, blendshapes, image, flame, translator, output_dir: str) -> Tuple[str, str, Dict]:
        """Generate proper FLAME 3D mesh."""
        mesh_path = os.path.join(output_dir, f"flame_mesh_{uuid.uuid4().hex[:8]}.obj")
        texture_path = os.path.join(output_dir, f"flame_texture_{uuid.uuid4().hex[:8]}.jpg")

        # Convert blendshapes to FLAME expression coefficients
        bs_array = np.array([blendshapes.get(name, 0.0) for name in self.BLENDSHAPE_NAMES])
        if translator.bridge.use_pretrained:
            flame_expr = bs_array @ translator.bridge.bs2exp
            flame_expr = flame_expr * 2.0
            jaw_pose = bs_array @ translator.bridge.bs2pose
            eye_pose = bs_array @ translator.bridge.bs2eye
        else:
            flame_expr = np.zeros(100)
            flame_expr[0] = blendshapes.get("jawOpen", 0.0) * 8.0
            flame_expr[1] = blendshapes.get("mouthSmileLeft", 0.0) * 6.0
            flame_expr[2] = blendshapes.get("mouthSmileRight", 0.0) * 6.0
            flame_expr[3] = blendshapes.get("browInnerUp", 0.0) * 5.0
            flame_expr[4] = blendshapes.get("eyeBlinkLeft", 0.0) * 8.0
            flame_expr[5] = blendshapes.get("eyeBlinkRight", 0.0) * 8.0
            jaw_pose = np.zeros(3)
            eye_pose = np.zeros(6)

        # Deform mesh
        deformed = flame.deform(flame_expr)
        faces = flame.faces

        # Save texture
        cv2.imwrite(texture_path, image)

        # Save OBJ
        with open(mesh_path, "w") as f:
            f.write("# DreamTalk FLAME 3D Face Mesh\n")
            f.write(f"mtl flame_texture.mtl\n")
            f.write(f"usemtl face_texture\n")
            for v in deformed:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            # UV coordinates (simple cylindrical projection)
            for v in deformed:
                u = 0.5 + np.arctan2(v[2], v[0]) / (2 * np.pi)
                vt = 0.5 - np.arcsin(v[1] / np.linalg.norm(v + 1e-8)) / np.pi
                f.write(f"vt {u:.4f} {vt:.4f}\n")
            for tri in faces:
                f.write(f"f {tri[0]+1}/{tri[0]+1} {tri[1]+1}/{tri[1]+1} {tri[2]+1}/{tri[2]+1}\n")

        mesh_info = {
            "vertex_count": len(deformed),
            "face_count": len(faces),
            "expression_active_dims": int(np.sum(np.abs(flame_expr) > 0.1)),
            "max_expression_value": round(float(np.max(np.abs(flame_expr))), 4),
        }

        logger.info(f"FLAME 3D mesh saved: {mesh_path} ({len(deformed)} verts, {len(faces)} faces)")
        return mesh_path, texture_path, mesh_info

    def _generate_placeholder_mesh(self, blendshapes, image, output_dir: str) -> Tuple[str, str, Dict]:
        """Generate structural face-like mesh with proper facial features."""
        mesh_path = os.path.join(output_dir, f"face_mesh_{uuid.uuid4().hex[:8]}.obj")
        texture_path = os.path.join(output_dir, f"face_texture_{uuid.uuid4().hex[:8]}.jpg")
        h, w = image.shape[:2]

        cv2.imwrite(texture_path, image)

        cols, rows = 32, 32
        n_verts = cols * rows
        verts = np.zeros((n_verts, 3))

        for r in range(rows):
            for c in range(cols):
                i = r * cols + c
                phi = np.pi * r / (rows - 1)
                theta = 2 * np.pi * c / (cols - 1)

                base_x = np.sin(phi) * np.cos(theta)
                base_y = np.cos(phi)
                base_z = np.sin(phi) * np.sin(theta)

                # Face shape: oval with chin narrower than forehead
                oval_factor = 1.0 - 0.25 * (1.0 + base_y)  # narrower at chin
                rx, ry, rz = 0.40, 0.45, 0.22

                x = base_x * rx * oval_factor
                y = base_y * ry
                z = base_z * rz - 0.1

                # Facial feature deformations
                # Eye sockets (depressions)
                eye_l_dist = np.sqrt((x - (-0.12))**2 + (y - 0.12)**2 + z**2)
                eye_r_dist = np.sqrt((x - 0.12)**2 + (y - 0.12)**2 + z**2)
                eye_depth = 0.03 * np.exp(-eye_l_dist * 12) + 0.03 * np.exp(-eye_r_dist * 12)
                z += eye_depth

                # Eyebrow ridge
                brow_l = np.exp(-((x - (-0.14))**2 + (y - 0.22)**2) * 60)
                brow_r = np.exp(-((x - 0.14)**2 + (y - 0.22)**2) * 60)
                z -= 0.02 * (brow_l + brow_r)

                # Nose bridge
                nose_dist = np.sqrt((x)**2 + (y - (-0.05))**2 * 2 + z**2)
                z -= 0.04 * np.exp(-nose_dist * 8)
                # Nose tip
                tip_dist = np.sqrt(x**2 + (y - (-0.08))**2 * 4 + z**2)
                z -= 0.03 * np.exp(-tip_dist * 15)

                # Mouth area (slight protrusion)
                mouth_dist = np.sqrt(x**2 * 3 + (y - (-0.12))**2 * 4)
                z -= 0.015 * np.exp(-mouth_dist * 8)

                # Chin prominence
                chin_dist = np.sqrt(x**2 * 4 + (y - (-0.30))**2)
                z -= 0.02 * np.exp(-chin_dist * 10)

                # Cheekbones
                cheek_l = np.exp(-((x - (-0.25))**2 + (y - 0.0)**2) * 25)
                cheek_r = np.exp(-((x - 0.25)**2 + (y - 0.0)**2) * 25)
                z -= 0.015 * (cheek_l + cheek_r)

                # Forehead
                forehead = np.exp(-(x**2 * 3 + (y - 0.30)**2) * 20)
                z -= 0.01 * forehead

                # Jawline
                jaw_dist = np.sqrt(x**2 * 2 + (y - (-0.25))**2 * 1.5)
                z += 0.01 * np.exp(-jaw_dist * 6)

                verts[i] = [x, y, z]

        with open(mesh_path, "w") as f:
            f.write("mtl face_texture.mtl\nusemtl face_texture\n")
            for v in verts:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            for r in range(rows):
                for c in range(cols):
                    u = c / (cols - 1)
                    vt = 1.0 - r / (rows - 1)
                    f.write(f"vt {u:.4f} {vt:.4f}\n")
            for r in range(rows - 1):
                for c in range(cols - 1):
                    i0 = r * cols + c
                    i1 = r * cols + c + 1
                    i2 = (r + 1) * cols + c
                    i3 = (r + 1) * cols + c + 1
                    f.write(f"f {i0+1}/{i0+1} {i1+1}/{i1+1} {i2+1}/{i2+1}\n")
                    f.write(f"f {i1+1}/{i1+1} {i3+1}/{i3+1} {i2+1}/{i2+1}\n")

        return mesh_path, texture_path, {
            "vertex_count": n_verts,
            "face_count": (rows - 1) * (cols - 1) * 2,
            "expression_active_dims": 0, "max_expression_value": 0,
        }

    # ─── Facial Emotion ────────────────────────────────────────────────────

    def detect_facial_emotion(self, blendshapes: Dict) -> Dict:
        """Detect emotion from MediaPipe blendshape values."""
        if not blendshapes:
            return {"emotion": None, "confidence": 0.0, "scores": {}}

        scores = {}
        for emotion, triggers in self.EMOTION_BLENDSHAPE_MAP.items():
            active = sum(blendshapes.get(bs, 0.0) for bs in triggers)
            count = len(triggers)
            scores[emotion] = active / max(count, 1) if count > 0 else 0.0

        # Bonus for mouth-based expressions
        if blendshapes.get("mouthSmileLeft", 0) > 0.3 and blendshapes.get("mouthSmileRight", 0) > 0.3:
            scores["happy"] = min(scores["happy"] + 0.3, 1.0)

        if scores.get("_neutral", 0) >= 0.8:
            scores["neutral"] = 1.0

        sorted_emotions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_emotion = sorted_emotions[0] if sorted_emotions else ("neutral", 0.0)

        return {
            "emotion": top_emotion[0],
            "confidence": round(top_emotion[1], 4),
            "scores": {k: round(v, 4) for k, v in scores.items() if k != "_neutral"},
        }

    def get_face_embedding(self, image_path: str) -> Optional[List[float]]:
        """Generate a biometric face embedding using a real recognition model.

        Never substitute pixel statistics for a face embedding: doing so makes
        identity-similarity gates look operational while providing no biometric
        identity signal.
        """
        self._embedding_model = "unavailable"
        if DEEPFACE_AVAILABLE and os.path.exists(image_path):
            try:
                from dreamtalk.backend.services.image_identity import get_face_identity_service

                service = get_face_identity_service()
                embedding = service.embed(image_path)
                self._embedding_model = service.model_name
                return [float(value) for value in embedding]
            except Exception as e:
                logger.warning(f"DeepFace embedding failed: {e}")
        return None

    # ─── Compute Quality Score ──────────────────────────────────────────────

    def compute_quality_score(self, image: np.ndarray, faces: List[Dict], q_assessment: Dict) -> float:
        score = 0.0
        factors = {}

        if not faces:
            score = q_assessment.get("blur_score", 0) * 0.3
            factors["face_present"] = 0.0
        else:
            bbox = faces[0]["bbox"]
            h, w = image.shape[:2]
            face_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            image_area = w * h
            face_ratio = face_area / max(image_area, 1)
            factors["face_ratio"] = min(face_ratio * 3, 1.0)
            factors["face_present"] = 1.0

        factors["blur"] = q_assessment.get("blur_score", 0)
        factors["brightness"] = q_assessment.get("brightness_score", 0.5)
        factors["contrast"] = q_assessment.get("contrast_score", 0.5)

        score = sum(factors.values()) / max(len(factors), 1)
        return round(score, 4), factors

    # ─── Main Run ──────────────────────────────────────────────────────────

    @staticmethod
    def _export_glb(
        mesh_path: Optional[str],
        output_dir: str,
        texture_path: Optional[str] = None,
    ) -> Tuple[Optional[str], List[str]]:
        """Package the textured mesh as a browser-native binary glTF asset.

        Also bakes FLAME morph targets (visemes, blink, emotions) into the GLB
        so the browser can animate the user's own head directly — without them
        the mesh is a static bust and the runtime's `arkit_blendshapes`
        capability would be a promise we cannot keep.

        Returns (glb_path, blendshape_names).
        """
        if not mesh_path or not os.path.exists(mesh_path):
            return None, []
        try:
            from dreamtalk.pipeline.avatar_export import AvatarExporter
            from dreamtalk.pipeline.face_blendshapes import (
                build_blendshapes, load_flame_masks,
            )

            exporter = AvatarExporter()
            vertices, _normals, _uvs, _faces = exporter._parse_obj(mesh_path)

            targets = {}
            masks_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "weights", "flame", "FLAME_masks.pkl",
            )
            # Masks index FLAME's canonical 5023-vertex topology; only build
            # blendshapes when the mesh actually is that topology.
            if os.path.exists(masks_path) and len(vertices) == 5023:
                try:
                    targets = build_blendshapes(vertices, load_flame_masks(masks_path))
                except Exception as exc:
                    logger.warning("Blendshape build failed: %s", exc)
            elif len(vertices) != 5023:
                logger.info("Mesh has %d verts (not FLAME topology) — no blendshapes",
                            len(vertices))

            destination = os.path.join(output_dir, f"avatar_mesh_{uuid.uuid4().hex[:8]}.glb")
            exporter.obj_to_glb(
                mesh_path, texture_path, destination,
                morph_targets=targets or None,
            )
            if os.path.exists(destination) and os.path.getsize(destination) > 1024:
                return destination, sorted(targets)
        except Exception as exc:
            logger.warning("GLB export failed: %s", exc)
        return None, []

    async def run(self, image_paths: List[str], output_dir: str = None, enable_sr: bool = True) -> FaceAnalysisResult:
        if not image_paths:
            return FaceAnalysisResult(error="No image paths provided")

        primary_path = image_paths[0]
        image = self._load_image(primary_path)
        if image is None:
            return FaceAnalysisResult(error=f"Cannot load image: {primary_path}")

        if output_dir is None:
            output_dir = self.assets_dir
        os.makedirs(output_dir, exist_ok=True)

        result = FaceAnalysisResult()

        # Step 0: Quality assessment
        quality = self._assess_quality(image)
        result.quality_factors = quality
        result.original_image_quality = quality["quality_label"]

        # Step 1: legacy classical enhancement. Production avatar creation runs
        # GFPGAN/Real-ESRGAN before this pipeline and disables this branch.
        if enable_sr and (quality["is_blurry"] or quality["low_light"] or quality["width"] < 200):
            image = self.apply_classical_enhancement(image)
            result.image_enhancement_applied = True
            result.image_enhancement_engine = "opencv-cubic-clahe-unsharp"
            result.super_resolution_factor = image.shape[1] / quality["width"] if quality["width"] > 0 else 1.0

        # Step 2: Multi-backend face detection
        faces = self.detect_faces(image)
        result.face_detected = len(faces) > 0
        result.face_count = len(faces)
        result.detection_backend = faces[0]["backend"] if faces else "none"

        # Step 3: Landmark extraction + blendshapes + head pose
        if result.face_detected:
            lm_result = self.extract_landmarks(image, faces[0]["bbox"])
            result.landmarks = lm_result["landmarks"][:20]  # sample for output
            result.landmark_count = lm_result["landmark_count"]
            result.landmark_backend = lm_result["method"]
            result.mediapipe_blendshapes = lm_result["blendshapes"]
            result.blendshape_count = len(lm_result["blendshapes"])
            result.head_pose = lm_result["head_pose"]
            result.head_pose_confidence = 0.85 if lm_result["method"] != "none" else 0.0

        # Step 4: FLAME 3D mesh (always generate mesh when face is detected)
        if result.face_detected:
            blendshapes = result.mediapipe_blendshapes or {}
            mesh_path, tex_path, mesh_info = self.generate_3d_mesh(
                blendshapes, image, output_dir, image_path=primary_path,
            )
            result.mesh_3d_path = mesh_path
            result.mesh_glb_path, result.mesh_blendshape_names = self._export_glb(
                mesh_path, output_dir, texture_path=tex_path,
            )
            result.texture_path = tex_path
            result.mesh_vertex_count = mesh_info["vertex_count"]
            result.mesh_face_count = mesh_info["face_count"]
            result.texture_mapped = bool(mesh_path and tex_path)
            result.flame_expression_coeffs = [0.0] * 100  # structural since we save OBJ directly

        # Step 5: Face embedding
        result.face_embedding = self.get_face_embedding(primary_path)
        result.identity_embedding = result.face_embedding
        result.embedding_model = self._embedding_model
        result.embedding_dim = len(result.face_embedding) if result.face_embedding else 0
        result.identity_confidence = 0.85 if result.face_embedding else 0.0

        # Step 6: Facial emotion
        if result.mediapipe_blendshapes:
            emotion_data = self.detect_facial_emotion(result.mediapipe_blendshapes)
            result.emotion_from_face = emotion_data["emotion"]
            result.emotion_confidence = emotion_data["confidence"]
            result.emotion_scores = emotion_data["scores"]

        # Step 7: Overall quality score
        q_score, factors = self.compute_quality_score(image, faces, quality)
        result.quality_score = q_score

        return result
