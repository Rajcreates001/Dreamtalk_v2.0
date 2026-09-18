# Dreamtalk - Face Engine
# Extracted from LivePortrait
import torch
import numpy as np


def headpose_pred_to_degree(pred):
    """Bin logits to degrees.

    The motion extractor predicts pitch, yaw and roll as 66-bin
    classification logits covering roughly -97.5..+97.5 degrees in 3 degree
    steps. The expected bin index times 3 gives a value in 0..198, and the
    offset recentres it on zero.

    That offset was -1 here instead of -97.5, which is not a small error: a
    frontal portrait came out at pitch 100.3, yaw 95.7, roll 96.8 degrees
    rather than 2.8, -1.8 and -0.7, so every head was rotated about a quarter
    turn before warping. The generator has no way to render that from a single
    frontal view and returned a saturated blob - which is what the portrait
    blink path had been producing, silently, for as long as it has existed.
    """
    device = pred.device
    idx_tensor = torch.arange(pred.shape[1], device=device).float()
    pred = torch.softmax(pred, dim=1)
    degree = torch.sum(pred * idx_tensor, dim=1) * 3 - 97.5
    return degree


def get_rotation_matrix(pitch, yaw, roll):
    bs = pitch.shape[0]
    device = pitch.device
    pitch = pitch * np.pi / 180
    yaw = yaw * np.pi / 180
    roll = roll * np.pi / 180

    # Handle both 1D (bs,) and 2D (bs, 1) inputs
    def _val(t):
        return t if t.dim() == 1 else t[:, 0]

    sin_pitch, cos_pitch = torch.sin(pitch), torch.cos(pitch)
    sin_yaw, cos_yaw = torch.sin(yaw), torch.cos(yaw)
    sin_roll, cos_roll = torch.sin(roll), torch.cos(roll)

    R_x = torch.zeros(bs, 3, 3, device=device)
    R_x[:, 0, 0] = 1
    R_x[:, 1, 1] = _val(cos_pitch)
    R_x[:, 1, 2] = -_val(sin_pitch)
    R_x[:, 2, 1] = _val(sin_pitch)
    R_x[:, 2, 2] = _val(cos_pitch)

    R_y = torch.zeros(bs, 3, 3, device=device)
    R_y[:, 0, 0] = _val(cos_yaw)
    R_y[:, 0, 2] = _val(sin_yaw)
    R_y[:, 1, 1] = 1
    R_y[:, 2, 0] = -_val(sin_yaw)
    R_y[:, 2, 2] = _val(cos_yaw)

    R_z = torch.zeros(bs, 3, 3, device=device)
    R_z[:, 0, 0] = _val(cos_roll)
    R_z[:, 0, 1] = -_val(sin_roll)
    R_z[:, 1, 0] = _val(sin_roll)
    R_z[:, 1, 1] = _val(cos_roll)
    R_z[:, 2, 2] = 1

    R = R_z @ R_y @ R_x
    return R
