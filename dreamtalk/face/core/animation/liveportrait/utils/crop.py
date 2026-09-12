# Dreamtalk - Face Engine
# Extracted from LivePortrait
import numpy as np
import cv2
from math import acos, cos, sin


DTYPE = np.float32


def _transform_img(img, matrix, dsize, border_mode=None):
    size = tuple(dsize) if isinstance(dsize, (tuple, list)) else (dsize, dsize)
    kwargs = {"borderMode": border_mode, "borderValue": (0, 0, 0)} if border_mode is not None else {}
    return cv2.warpAffine(img, matrix[:2], size, flags=cv2.INTER_LINEAR, **kwargs)


def _transform_pts(points, matrix=None, M=None):
    matrix = matrix if matrix is not None else M
    return points @ matrix[:2, :2].T + matrix[:2, 2]


def _face_axis(points):
    """Return stable eye/mouth centers for 5- or 203-point landmarks."""
    if points.shape[0] == 5:
        eye = (points[0] + points[1]) / 2
        mouth = (points[3] + points[4]) / 2
    elif points.shape[0] >= 203:
        left_eye = np.mean(points[[0, 6, 12, 18]], axis=0)
        right_eye = np.mean(points[[24, 30, 36, 42]], axis=0)
        eye = (left_eye + right_eye) / 2
        mouth = (points[48] + points[66]) / 2
    else:
        raise ValueError(f"Unsupported landmark shape: {points.shape}")
    return eye, mouth


def _crop_matrix(points, dsize, scale=1.5, vx_ratio=0.0, vy_ratio=-0.1, flag_do_rot=True):
    eye, mouth = _face_axis(points)
    uy = mouth - eye
    length = float(np.linalg.norm(uy))
    uy = uy / length if length > 1e-3 else np.array([0.0, 1.0], dtype=DTYPE)
    ux = np.array([uy[1], -uy[0]], dtype=DTYPE)
    rotation = np.array([ux, uy], dtype=DTYPE)
    center0 = np.mean(points, axis=0)
    rotated = (points - center0) @ rotation.T
    minimum, maximum = np.min(rotated, axis=0), np.max(rotated, axis=0)
    local_center = (minimum + maximum) / 2
    side = float(np.max(maximum - minimum) * scale)
    if side <= 1.0:
        raise ValueError("Face landmarks do not define a valid crop")
    center = center0 + ux * local_center[0] + uy * local_center[1]
    center += ux * vx_ratio * side + uy * vy_ratio * side
    factor = dsize / side
    target = dsize / 2.0
    if flag_do_rot:
        angle = acos(float(np.clip(ux[0], -1.0, 1.0)))
        if ux[1] < 0:
            angle = -angle
        c, s = cos(angle), sin(angle)
        matrix = np.array([
            [factor * c, factor * s, target - factor * (c * center[0] + s * center[1])],
            [-factor * s, factor * c, target - factor * (-s * center[0] + c * center[1])],
        ], dtype=DTYPE)
    else:
        matrix = np.array([
            [factor, 0, target - factor * center[0]],
            [0, factor, target - factor * center[1]],
        ], dtype=DTYPE)
    return matrix


def crop_image(img, points, dsize=224, scale=1.5, vx_ratio=0.0,
               vy_ratio=-0.1, flag_do_rot=True, **_kwargs):
    """Crop a face and retain transforms used by LivePortrait paste-back."""
    matrix = _crop_matrix(
        np.asarray(points, dtype=DTYPE), dsize, scale, vx_ratio, vy_ratio, flag_do_rot
    )
    image_crop = _transform_img(img, matrix, dsize)
    points_crop = _transform_pts(points, matrix)
    original_to_crop = np.vstack([matrix, np.array([0, 0, 1], dtype=DTYPE)])
    crop_to_original = np.linalg.inv(original_to_crop)
    return {
        "M_o2c": original_to_crop,
        "M_c2o": crop_to_original,
        "img_crop": image_crop,
        "pt_crop": points_crop,
        "lmk_crop": points_crop,
    }


def prepare_paste_back(mask_crop, M_c2o, dsize):
    """
    Prepare the mask for paste-back operation.
    mask_crop: HxWx3 mask in crop space
    M_c2o: 2x3 affine matrix from crop to original
    dsize: (width, height) of original image
    """
    mask_ori = cv2.warpAffine(mask_crop, M_c2o[:2], dsize, flags=cv2.INTER_LINEAR)
    mask_ori_float = mask_ori.astype(np.float32) / 255.
    return mask_ori_float


def paste_back(I_p_i, M_c2o, img_ori, mask_ori_float):
    """
    Paste the generated face back to the original image.
    I_p_i: HxWx3 generated face (uint8, 256x256)
    M_c2o: 2x3 affine matrix
    img_ori: HxWx3 original image
    mask_ori_float: HxWx3 float mask
    """
    I_p_i_warped = cv2.warpAffine(I_p_i, M_c2o[:2], (img_ori.shape[1], img_ori.shape[0]), flags=cv2.INTER_LINEAR)
    I_p_pstbk = (I_p_i_warped * mask_ori_float + img_ori * (1 - mask_ori_float)).astype(np.uint8)
    return I_p_pstbk
