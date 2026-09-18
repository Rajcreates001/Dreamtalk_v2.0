# Dreamtalk - Face Engine
# Extracted from LivePortrait
import numpy as np


def calc_eye_close_ratio(lmk):
    """Eye aperture as height over width, one value per eye.

    The landmark array is LivePortrait's 203-point layout, where the left eye
    contour is points 0..23 and the right 24..47. The aperture is the vertical
    span over the horizontal: points 6 and 18 against 0 and 12 for the left
    eye, and the same pattern offset by 24 for the right.

    This read points 96..108 and 108..120 with a six-point dlib convention
    instead - a different landmark layout entirely - and returned 1.34 and 1.35
    for a normally open eye. The true figures for that same photograph are
    0.225 and 0.246. An open eye measures roughly 0.25 to 0.40 and a closed one
    near zero, so the retargeting network was being handed a value four times
    outside anything it saw in training, and asked to close an eye it believed
    was impossibly wide. It responded with a keypoint delta of 0.003, far too
    small to move an eyelid, which is why blinks did not appear.

    Two values and not three: the retargeter takes 63 keypoint values plus two
    source-eye ratios plus one target, and a third source average breaks the
    input width.
    """
    if lmk is None:
        return np.zeros((1, 2), dtype=np.float32)
    left_eye_ratio = _distance_ratio(lmk, 6, 18, 0, 12)
    right_eye_ratio = _distance_ratio(lmk, 30, 42, 24, 36)
    return np.concatenate([left_eye_ratio, right_eye_ratio], axis=1)


def _distance_ratio(lmk, idx1, idx2, idx3, idx4, eps=1e-6):
    """|p(idx1) - p(idx2)| / |p(idx3) - p(idx4)|, batched."""
    return (np.linalg.norm(lmk[:, idx1] - lmk[:, idx2], axis=1, keepdims=True)
            / (np.linalg.norm(lmk[:, idx3] - lmk[:, idx4], axis=1, keepdims=True)
               + eps)).astype(np.float32)


def calc_eye_ratio(eye_landmarks):
    """Kept for callers passing a pre-sliced six-point eye contour."""
    eye_ratio = np.zeros((eye_landmarks.shape[0], 1), dtype=np.float32)
    for i in range(eye_landmarks.shape[0]):
        eye_ratio[i, 0] = np.linalg.norm(eye_landmarks[i, 1] - eye_landmarks[i, 5]) / (
            np.linalg.norm(eye_landmarks[i, 0] - eye_landmarks[i, 3]) + 1e-8
        )
    return eye_ratio


def calc_lip_close_ratio(lmk):
    if lmk is None:
        return np.zeros((1, 2), dtype=np.float32)
    lip_ratio = np.zeros((lmk.shape[0], 1), dtype=np.float32)
    for i in range(lmk.shape[0]):
        lip_ratio[i, 0] = np.linalg.norm(lmk[i, 64] - lmk[i, 60]) / (
            np.linalg.norm(lmk[i, 54] - lmk[i, 48]) + 1e-8
        )
    return lip_ratio
