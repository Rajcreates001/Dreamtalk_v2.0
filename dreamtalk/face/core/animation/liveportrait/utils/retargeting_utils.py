# Dreamtalk - Face Engine
# Extracted from LivePortrait
import numpy as np


def calc_eye_close_ratio(lmk):
    if lmk is None:
        return np.zeros((1, 3), dtype=np.float32)
    left_eye_ratio = calc_eye_ratio(lmk[:, 96:108])
    right_eye_ratio = calc_eye_ratio(lmk[:, 108:120])
    eye_close_ratio = np.concatenate([left_eye_ratio, right_eye_ratio, (left_eye_ratio + right_eye_ratio) / 2], axis=1)
    return eye_close_ratio


def calc_eye_ratio(eye_landmarks):
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
