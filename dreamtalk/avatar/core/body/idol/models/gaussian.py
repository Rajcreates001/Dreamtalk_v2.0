# Dreamtalk - 3D Avatar Module
# Extracted from IDOL
# 3D Gaussian Splatting renderer with diff-gaussian-rasterization

import math
import torch
import torch.nn as nn
from diff_gaussian_rasterization import GaussianRasterizationSettings, GaussianRasterizer


def batch_rodrigues(rot_vecs, epsilon=1e-8):
    """Calculate rotation matrices from batch of axis-angle vectors.

    Args:
        rot_vecs: torch.tensor Nx3 array of N axis-angle vectors
    Returns:
        R: torch.tensor Nx3x3 rotation matrices
    """
    batch_size = rot_vecs.shape[0]
    device, dtype = rot_vecs.device, rot_vecs.dtype

    angle = torch.norm(rot_vecs + 1e-8, dim=1, keepdim=True)
    rot_dir = rot_vecs / angle

    cos = torch.unsqueeze(torch.cos(angle), dim=1)
    sin = torch.unsqueeze(torch.sin(angle), dim=1)

    rx, ry, rz = torch.split(rot_dir, 1, dim=1)
    K = torch.zeros((batch_size, 3, 3), dtype=dtype, device=device)
    zeros = torch.zeros((batch_size, 1), dtype=dtype, device=device)
    K = torch.cat([zeros, -rz, ry, rz, zeros, -rx, -ry, rx, zeros], dim=1).view((batch_size, 3, 3))

    ident = torch.eye(3, dtype=dtype, device=device).unsqueeze(dim=0)
    rot_mat = ident + sin * K + (1 - cos) * torch.bmm(K, K)
    return rot_mat


def strip_symmetric(L):
    """Extract symmetric covariance matrix components."""
    uncertainty = torch.zeros((L.shape[0], 6), dtype=torch.float, device=L.device)
    uncertainty[:, 0] = L[:, 0, 0]
    uncertainty[:, 1] = L[:, 0, 1]
    uncertainty[:, 2] = L[:, 0, 2]
    uncertainty[:, 3] = L[:, 1, 1]
    uncertainty[:, 4] = L[:, 1, 2]
    uncertainty[:, 5] = L[:, 2, 2]
    return uncertainty


def get_covariance(scaling, rotation, scaling_modifier=1):
    """Compute 3D covariance from scaling and rotation."""
    L = torch.zeros_like(rotation)
    L[:, 0, 0] = scaling[:, 0]
    L[:, 1, 1] = scaling[:, 1]
    L[:, 2, 2] = scaling[:, 2]
    actual_covariance = rotation @ (L**2) @ rotation.permute(0, 2, 1)
    return strip_symmetric(actual_covariance)


def build_rotation(r):
    """Build rotation matrix from quaternion."""
    norm = torch.sqrt(r[:, 0]**2 + r[:, 1]**2 + r[:, 2]**2 + r[:, 3]**2)
    q = r / norm[:, None]
    R = torch.zeros((q.size(0), 3, 3), device=q.device)
    r_ = q[:, 0]
    x = q[:, 1]
    y = q[:, 2]
    z = q[:, 3]
    R[:, 0, 0] = 1 - 2 * (y*y + z*z)
    R[:, 0, 1] = 2 * (x*y - r_*z)
    R[:, 0, 2] = 2 * (x*z + r_*y)
    R[:, 1, 0] = 2 * (x*y + r_*z)
    R[:, 1, 1] = 1 - 2 * (x*x + z*z)
    R[:, 1, 2] = 2 * (y*z - r_*x)
    R[:, 2, 0] = 2 * (x*z - r_*y)
    R[:, 2, 1] = 2 * (y*z + r_*x)
    R[:, 2, 2] = 1 - 2 * (x*x + y*y)
    return R


def get_proj_yy(f, image_size, far, near):
    """Get OpenGL-style projection matrix."""
    opengl_proj = torch.tensor([
        [2 * f / image_size[0], 0.0, 0.0, 0.0],
        [0.0, 2 * f / image_size[1], 0.0, 0.0],
        [0.0, 0.0, far / (far - near), -(far * near) / (far - near)],
        [0.0, 0.0, 1.0, 0.0]
    ]).float().unsqueeze(0).transpose(1, 2)
    return opengl_proj


def get_fov(focal, princpt, img_shape):
    """Compute field of view from focal length and image shape."""
    fov_x = 2 * torch.atan(img_shape[1] / (2 * focal[0]))
    fov_y = 2 * torch.atan(img_shape[0] / (2 * focal[1]))
    _dev = "cuda" if torch.cuda.is_available() else "cpu"
    return torch.FloatTensor([fov_x, fov_y]).to(_dev)


class GRenderer(nn.Module):
    """3D Gaussian Splatting renderer using diff-gaussian-rasterization."""

    def __init__(self, image_size=256, f=5000, near=0.01, far=40, bg_color=0):
        super().__init__()
        self.image_size = image_size if isinstance(image_size, (list, tuple)) else [image_size, image_size]
        self.tanfov = 2 * math.atan(self.image_size[0] / (2 * f))

        bg = torch.tensor([0, 0, 0] if bg_color == 0 else [1, 1, 1], dtype=torch.float32)
        self.register_buffer("bg", bg)

        opengl_proj = get_proj_yy(f, self.image_size, far, near)
        self.register_buffer("opengl_proj", opengl_proj)

    def prepare(self, cameras):
        """Prepare rasterizer settings from camera parameters."""
        if cameras.shape[-1] == 20:
            w2c = cameras[4:].reshape(4, 4)
            cam_center = torch.inverse(w2c)[:3, 3]
            intrisics = cameras[:4]
            fov = get_fov(intrisics[0:2], intrisics[2].item(), self.image_size)
            tanfovx = fov[1]
            tanfovy = fov[1]
            w2c = w2c.unsqueeze(0).transpose(1, 2)
            proj_matrix = get_proj_yy(intrisics[0], self.image_size, 100, 0.01).to(torch.float32).to(intrisics.device)
            full_proj = torch.bmm(w2c, proj_matrix).to(torch.float32)
        elif cameras.shape[-1] == 19:
            cam_center = cameras[:3]
            w2c = cameras[3:].reshape(4, 4)
            w2c = w2c.unsqueeze(0).transpose(1, 2)
            full_proj = w2c.bmm(self.opengl_proj).to(torch.float32)
            tanfovx = self.tanfov
            tanfovy = self.tanfov
        else:
            raise ValueError(f"Unsupported camera format: {cameras.shape[-1]} (expected 19 or 20)")

        self.raster_settings = GaussianRasterizationSettings(
            image_height=self.image_size[1],
            image_width=self.image_size[0],
            tanfovx=tanfovx,
            tanfovy=tanfovy,
            bg=self.bg.to(cameras.dtype),
            scale_modifier=1.0,
            viewmatrix=w2c,
            projmatrix=full_proj,
            sh_degree=0,
            campos=cam_center,
            prefiltered=False,
            debug=False,
            antialiasing=True,
        )
        self.rasterizer = GaussianRasterizer(raster_settings=self.raster_settings)

    def render_gaussian(self, means3D, colors_precomp, rotations, opacities, scales, cov3D_precomp=None):
        """Render 3D Gaussians to 2D image."""
        screenspace_points = torch.zeros_like(means3D, dtype=means3D.dtype, requires_grad=True, device=means3D.device)
        try:
            screenspace_points.retain_grad()
        except Exception:
            pass

        if cov3D_precomp is not None:
            image, _, _ = self.rasterizer(
                means3D=means3D, colors_precomp=colors_precomp,
                opacities=opacities, means2D=screenspace_points, cov3D_precomp=cov3D_precomp
            )
        else:
            image, _, _ = self.rasterizer(
                means3D=means3D, colors_precomp=colors_precomp,
                rotations=torch.nn.functional.normalize(rotations), opacities=opacities,
                scales=scales, means2D=screenspace_points
            )
        return image


class Gaussian3DCoeff:
    """Gaussian 3D coefficient computation."""

    @staticmethod
    def compute(xyzs, covs):
        """Compute 3D Gaussian response.

        Args:
            xyzs: [N, 3] point positions
            covs: [N, 6] covariance matrix components
        Returns:
            weights: [N] Gaussian weights
        """
        x, y, z = xyzs[:, 0], xyzs[:, 1], xyzs[:, 2]
        a, b, c, d, e, f = covs[:, 0], covs[:, 1], covs[:, 2], covs[:, 3], covs[:, 4], covs[:, 5]

        inv_det = 1 / (a * d * f + 2 * e * c * b - e**2 * a - c**2 * d - b**2 * f + 1e-24)
        inv_a = (d * f - e**2) * inv_det
        inv_b = (e * c - b * f) * inv_det
        inv_c = (e * b - c * d) * inv_det
        inv_d = (a * f - c**2) * inv_det
        inv_e = (b * c - e * a) * inv_det
        inv_f = (a * d - b**2) * inv_det

        power = -0.5 * (x**2 * inv_a + y**2 * inv_d + z**2 * inv_f) - x * y * inv_b - x * z * inv_c - y * z * inv_e
        power[power > 0] = -1e10
        return torch.exp(power)
