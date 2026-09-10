# Dreamtalk - 3D Avatar Module
# Extracted from IDOL
# Inference utilities: SMPL-X loading, camera construction, image processing

import os
import json
import math
import cv2
import torch
import numpy as np
import PIL.Image
from pathlib import Path
from PIL import Image
from typing import Any, List, Optional
from torchvision.transforms import ToTensor
from rembg import remove
from pytorch3d.transforms import axis_angle_to_matrix, matrix_to_axis_angle
from scipy.spatial.transform import Rotation
import imageio


def get_hand_pose_mean():
    """Get mean hand pose for SMPL-X."""
    return np.array([[0.11167871, 0.04289218, -0.41644183, 0.10881133, -0.06598568,
                      -0.75622, -0.09639297, -0.09091566, -0.18845929, -0.11809504,
                      0.05094385, -0.5295845, -0.14369841, 0.0552417, -0.7048571,
                      -0.01918292, -0.09233685, -0.3379135, -0.45703298, -0.19628395,
                      -0.6254575, -0.21465237, -0.06599829, -0.50689423, -0.36972436,
                      -0.06034463, -0.07949023, -0.1418697, -0.08585263, -0.63552827,
                      -0.3033416, -0.05788098, -0.6313892, -0.17612089, -0.13209307,
                      -0.37335458, 0.8509643, 0.27692273, -0.09154807, -0.49983943,
                      0.02655647, 0.05288088, 0.5355592, 0.04596104, -0.27735803,
                      0.11167871, -0.04289218, 0.41644183, 0.10881133, 0.06598568,
                      0.75622, -0.09639297, 0.09091566, 0.18845929, -0.11809504,
                      -0.05094385, 0.5295845, -0.14369841, -0.0552417, 0.7048571,
                      -0.01918292, 0.09233685, 0.3379135, -0.45703298, 0.19628395,
                      0.6254575, -0.21465237, 0.06599829, 0.50689423, -0.36972436,
                      0.06034463, 0.07949023, -0.1418697, 0.08585263, 0.63552827,
                      -0.3033416, 0.05788098, 0.6313892, -0.17612089, 0.13209307,
                      0.37335458, 0.8509643, -0.27692273, 0.09154807, -0.49983943,
                      -0.02655647, -0.05288088, 0.5355592, -0.04596104, 0.27735803]])


def reset_first_frame_rotation(root_orient, trans):
    """Normalize root orientation to identity at first frame, keeping relative motion.

    Args:
        root_orient: (N, 3) axis-angle
        trans: (N, 3) translation
    Returns:
        new_root_orient, new_trans
    """
    R_0 = axis_angle_to_matrix(root_orient[0:1])
    R_0_inv = torch.inverse(R_0)
    new_root_orient, new_trans = [], []
    for i in range(root_orient.shape[0]):
        R_i = axis_angle_to_matrix(root_orient[i:i + 1])
        R_new = torch.matmul(R_0_inv, R_i)
        axis_angle_new = matrix_to_axis_angle(R_new)
        new_root_orient.append(axis_angle_new)
        trans_i = trans[i:i + 1]
        trans_new = torch.matmul(R_0_inv, trans_i.T).T
        new_trans.append(trans_new)
    new_root_orient = torch.cat(new_root_orient, dim=0)
    new_trans = torch.cat(new_trans, dim=0)
    new_trans = new_trans - new_trans[[0], :]
    return new_root_orient, new_trans


def rotation_matrix_to_rodrigues(rotation_matrices):
    """Convert rotation matrices to Rodrigues vectors."""
    reshaped = rotation_matrices.reshape(-1, 3, 3)
    rotation = Rotation.from_matrix(reshaped.cpu().numpy())
    rodrigues = rotation.as_rotvec()
    return rodrigues


def load_smplify_json(smplx_smplify_path):
    """Load SMPLify-X output (SMPL-X params + camera)."""
    with open(smplx_smplify_path) as f:
        data = json.load(f)
    RT = torch.cat([torch.Tensor(data["camera"]["R"]),
                    torch.Tensor(data["camera"]["t"]).reshape(3, 1) * 2], dim=1)
    RT = torch.cat([RT, torch.Tensor([[0, 0, 0, 1]])], dim=0)
    intri = torch.Tensor(data["camera"]["focal"] + data["camera"]["princpt"])
    smpl = data
    global_orient = np.array(smpl["root_pose"]).reshape(1, -1)
    body_pose = np.array(smpl["body_pose"]).reshape(1, -1)
    shape = np.array(smpl["betas_save"]).reshape(1, -1)[:, :10]
    left_hand = np.array(smpl["lhand_pose"]).reshape(1, -1)
    right_hand = np.array(smpl["rhand_pose"]).reshape(1, -1)
    smpl_param_ref = np.concatenate([
        np.array([[1.]]), np.array(smpl["trans"]).reshape(1, 3),
        global_orient, body_pose, shape, left_hand, right_hand,
        np.array(smpl["jaw_pose"]).reshape(1, -1),
        np.zeros((1, 3)), np.zeros((1, 3)), np.zeros((1, 10))
    ], axis=1)
    return RT, intri, torch.Tensor(smpl_param_ref).reshape(-1)


def load_image(input_path, output_folder, remove_bg=True, image_frame_ratio=None):
    """Load and preprocess image: background removal, resize, center crop."""
    input_img_path = Path(input_path)
    save_path = os.path.join(output_folder, input_img_path.name)
    image = Image.open(input_img_path)

    if image.mode == "RGBA":
        pass
    elif remove_bg:
        image = remove(image.convert("RGBA"), alpha_matting=True)

    image_arr = np.array(image)
    in_w, in_h = image_arr.shape[:2]
    ret, mask = cv2.threshold(np.array(image.split()[-1]), 0, 255, cv2.THRESH_BINARY)
    x, y, w, h = cv2.boundingRect(mask)
    max_size = max(w, h)
    side_len = int(max_size / image_frame_ratio) if image_frame_ratio else int(max_size / 0.85)

    padded_image = np.zeros((side_len, side_len, 4), dtype=np.uint8)
    center = side_len // 2
    padded_image[center - h // 2:center - h // 2 + h, center - w // 2:center - w // 2 + w] = image_arr[y:y + h, x:x + w]
    rgba = Image.fromarray(padded_image).resize((896, 896), Image.LANCZOS)
    rgba = rgba.crop([128, 0, 640 + 128, 896])
    rgba_arr = np.array(rgba) / 255.0
    rgb = rgba_arr[..., :3] * rgba_arr[..., -1:] + (1 - rgba_arr[..., -1:])
    return ToTensor()(Image.fromarray((rgb * 255).astype(np.uint8)))


def prepare_camera(resolution_x=640, resolution_y=640, focal_length=600,
                   sensor_width=32, camera_dist=20, num_views=1, strides=1):
    """Prepare camera intrinsics and extrinsics."""
    def look_at(camera_position, target_position, up_vector):
        forward = -(camera_position - target_position) / np.linalg.norm(camera_position - target_position)
        right = np.cross(up_vector, forward)
        up = np.cross(forward, right)
        return np.column_stack((right, up, forward))

    focal_length = focal_length * (resolution_y / sensor_width)
    K = np.array([[focal_length, 0, resolution_x // 2],
                  [0, focal_length, resolution_y // 2],
                  [0, 0, 1]])

    camera_pose_list = []
    for frame_idx in range(0, num_views, strides):
        phi = math.radians(90)
        theta = (3 / 4) * math.pi * 2
        camera_location = np.array([
            camera_dist * math.sin(phi) * math.cos(theta),
            camera_dist * math.cos(phi),
            -camera_dist * math.sin(phi) * math.sin(theta),
        ])
        camera_pose = np.eye(4)
        camera_pose[:3, 3] = camera_location
        rotation_matrix = look_at(camera_location, np.array([0.0, 0.0, 0.0]), np.array([0.0, -1.0, 0.0]))
        camera_pose[:3, :3] = rotation_matrix
        camera_pose_list.append(camera_pose)
    return K, camera_pose_list


def construct_camera(K, cam_list, device=None):
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    """Construct camera tensor from intrinsics and extrinsics list."""
    num_imgs = len(cam_list)
    front_idx = num_imgs // 4 * 3
    cam_list = cam_list[front_idx:] + cam_list[:front_idx]
    cam_raw = np.array(cam_list)
    cam_raw[:, :3, 3] = cam_raw[:, :3, 3]
    cam = np.linalg.inv(cam_raw)
    cam = torch.Tensor(cam)
    intrics = torch.Tensor([K[0, 0], K[1, 1], K[0, 2], K[1, 2]]).reshape(-1)
    scale = 0.5
    trans = [0, 0.2, 0]
    trans_bt = torch.Tensor(trans).reshape(1, 3, 1).expand(cam.shape[0], 3, 1)
    cam[:, :3, 3] = cam[:, :3, 3] + torch.bmm(cam[:, :3, :3], trans_bt).reshape(-1, 3)
    cam[:, :3, :3] = cam[:, :3, :3] * scale
    cam_w2c = cam
    poses = []
    for i_cam in range(cam.shape[0]):
        poses.append(torch.cat([
            intrics.reshape(-1).to(torch.float32),
            cam_w2c[i_cam].to(torch.float32).reshape(-1),
        ], dim=0))
    cameras = torch.stack(poses).to(device)
    return cameras


def get_name_str(name):
    """Extract base name from path."""
    return os.path.basename(os.path.dirname(name)) + os.path.basename(name)


def load_smplx_from_npy(smplx_path, device=None):
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    """Load SMPL-X parameters from .npy file."""
    hand_mean = get_hand_pose_mean().reshape(-1)
    data = np.load(smplx_path, allow_pickle=True)
    smplx_dict = {
        "root_orient": data[:, :3],
        "pose_body": data[:, 3:66],
        "pose_hand": data[:, 66:156],
        "pose_jaw": data[:, 156:159],
        "face_expr": data[:, 159:209],
        "face_shape": data[:, 209:309],
        "trans": data[:, 309:312],
        "betas": data[:, 312:],
    }
    smplx_param_list = []
    for i in range(min(1799, len(data))):
        smplx_param = np.concatenate([
            np.array([1]), smplx_dict["trans"][i], smplx_dict["root_orient"][i],
            smplx_dict["pose_body"][i], np.zeros(10),
            smplx_dict["pose_hand"][i] - hand_mean,
            smplx_dict["pose_jaw"][i], np.zeros(6),
            smplx_dict["face_expr"][i][:10]
        ], axis=0).reshape(1, -1)
        smplx_param_list.append(smplx_param)
    return torch.Tensor(np.concatenate(smplx_param_list, 0)).to(device)


def load_smplx_from_json(smplx_path, device=None):
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    """Load SMPL-X parameters from .json (Motion-X format)."""
    hand_mean = get_hand_pose_mean().reshape(-1)
    with open(smplx_path, "r") as f:
        data = json.load(f)
    smplx_param_list = []
    for par in data["annotations"]:
        k = par["smplx_params"]
        for key in k:
            k[key] = np.array(k[key])
        smplx_param = np.concatenate([
            np.array([1]), k["trans"],
            k["root_orient"] * np.array([1, 1, 1]),
            k["pose_body"], np.zeros(10),
            k["pose_hand"] - hand_mean, k["pose_jaw"],
            np.zeros(6), np.zeros(10)
        ], axis=0).reshape(1, -1)
        smplx_param_list.append(smplx_param)
    return torch.Tensor(np.concatenate(smplx_param_list, 0)).to(device)


def add_root_rotate_to_smplx(smpl_tmp, frames_num=180, device=None):
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    """Add 360-degree root rotation to SMPL-X params for view generation."""
    from dreamtalk.avatar.core.body.idol.models.gaussian import batch_rodrigues
    initial_matrix = batch_rodrigues(smpl_tmp.reshape(1, 189)[:, 4:7]).cpu().numpy()
    all_smpl = []
    for idx_f in range(frames_num):
        new_smpl = smpl_tmp.clone()
        angle = 360 // frames_num * idx_f
        y_angle = np.radians(angle)
        y_rotation_matrix = np.array([
            [np.cos(y_angle), 0, np.sin(y_angle)],
            [0, 1, 0],
            [-np.sin(y_angle), 0, np.cos(y_angle)],
        ])
        final_matrix = y_rotation_matrix[None] @ initial_matrix
        new_smpl[4:7] = torch.Tensor(rotation_matrix_to_rodrigues(torch.Tensor(final_matrix))).to(device)
        all_smpl.append(new_smpl)
    return torch.stack(all_smpl, 0).to(device)


def get_image_dimensions(input_path):
    """Get image height and width."""
    with Image.open(input_path) as img:
        return img.height, img.width


def construct_camera_from_motionx(smplx_path, device=None):
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    """Construct camera from Motion-X format."""
    with open(smplx_path, "r") as f:
        data = json.load(f)
    cam_exts, cam_ints = [], []
    for par in data["annotations"]:
        cam = par["cam_params"]
        R = np.array(cam["cam_R"])
        K = np.array(cam["intrins"])
        T = np.array(cam["cam_T"])
        cam["cam_T"][1] = -cam["cam_T"][1]
        cam["cam_T"][2] = -cam["cam_T"][2]
        extrix = np.eye(4)
        extrix[:3, :3] = R
        extrix[:3, 3] = T
        cam_exts.append(extrix)
        cam_ints.append(K)
    cameras = torch.cat([
        torch.Tensor(cam_ints).to(device).reshape(-1, 4),
        torch.Tensor(np.array(cam_exts)).to(device).reshape(-1, 16)
    ], dim=-1).reshape(-1, 1, 20)
    return cameras


def save_video(frames, output_path, fps=30):
    """Save tensor frames (N, C, H, W) to video."""
    writer = imageio.get_writer(output_path, fps=fps)
    for frame in frames:
        img = (frame.permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
        writer.append_data(img)
    writer.close()


def images_to_video(images, output_path, fps=30):
    """Save image tensor (N, C, H, W) to video."""
    frames = [(img.permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8) for img in images]
    imageio.mimwrite(output_path, np.stack(frames), fps=fps, quality=10)


def remove_background(image, rembg_session=None, force=False, **rembg_kwargs):
    """Remove background from PIL image."""
    do_remove = True
    if image.mode == "RGBA" and image.getextrema()[3][0] < 255:
        do_remove = False
    if do_remove or force:
        image = remove(image, session=rembg_session, **rembg_kwargs)
    return image


def resize_foreground(image, ratio):
    """Resize foreground to fill a square canvas at given ratio."""
    image = np.array(image)
    assert image.shape[-1] == 4
    alpha = np.where(image[..., 3] > 0)
    y1, y2, x1, x2 = alpha[0].min(), alpha[0].max(), alpha[1].min(), alpha[1].max()
    fg = image[y1:y2, x1:x2]
    size = max(fg.shape[0], fg.shape[1])
    ph0, pw0 = (size - fg.shape[0]) // 2, (size - fg.shape[1]) // 2
    ph1, pw1 = size - fg.shape[0] - ph0, size - fg.shape[1] - pw0
    new_image = np.pad(fg, ((ph0, ph1), (pw0, pw1), (0, 0)),
                       mode="constant", constant_values=((0, 0), (0, 0), (0, 0)))
    new_size = int(new_image.shape[0] / ratio)
    ph0, pw0 = (new_size - size) // 2, (new_size - size) // 2
    ph1, pw1 = new_size - size - ph0, new_size - size - pw0
    new_image = np.pad(new_image, ((ph0, ph1), (pw0, pw1), (0, 0)),
                       mode="constant", constant_values=((0, 0), (0, 0), (0, 0)))
    return PIL.Image.fromarray(new_image)
