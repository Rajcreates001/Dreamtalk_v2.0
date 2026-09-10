import pickle
import numpy as np
from typing import Optional, Tuple, List

def _to_rodrigues(rotvec: np.ndarray) -> np.ndarray:
    theta = np.linalg.norm(rotvec)
    if theta < 1e-8:
        return np.eye(3, dtype=rotvec.dtype)
    axis = rotvec / theta
    c, s = np.cos(theta), np.sin(theta)
    K = np.array([
        [0, -axis[2], axis[1]],
        [axis[2], 0, -axis[0]],
        [-axis[1], axis[0], 0],
    ], dtype=rotvec.dtype)
    return c * np.eye(3, dtype=rotvec.dtype) + s * K + (1 - c) * np.outer(axis, axis)

def _euler_to_rotmat(euler: np.ndarray) -> np.ndarray:
    rx, ry, rz = euler
    Rx = np.array([
        [1, 0, 0],
        [0, np.cos(rx), -np.sin(rx)],
        [0, np.sin(rx), np.cos(rx)],
    ])
    Ry = np.array([
        [np.cos(ry), 0, np.sin(ry)],
        [0, 1, 0],
        [-np.sin(ry), 0, np.cos(ry)],
    ])
    Rz = np.array([
        [np.cos(rz), -np.sin(rz), 0],
        [np.sin(rz), np.cos(rz), 0],
        [0, 0, 1],
    ])
    return Rz @ Ry @ Rx


class FLAMEModel:
    """FLAME 2020 parametric face model with full shape + pose + expression."""

    KINEMATIC_CHAIN = [(0, -1), (1, 0), (2, 0), (3, 1), (4, 2), (5, 3), (6, 4)]
    JOINT_NAMES = ["root", "jaw", "left_eye", "right_eye", "neck", "head", "spine"]

    def __init__(self, model_path: str):
        with open(model_path, "rb") as f:
            data = pickle.load(f, encoding="latin1")

        self.v_template: np.ndarray = data["v_template"]
        self.shapedirs: np.ndarray = data["shapedirs"]
        self.faces: np.ndarray = data["f"]
        self.J: np.ndarray = data.get("J_regressor", None)
        self.kintree_table: np.ndarray = data.get("kintree_table", None)
        self.weights: np.ndarray = data.get("weights", None)
        self.posedirs: np.ndarray = data.get("posedirs", None)
        self.joints: np.ndarray = None

        self.expression_basis = self.shapedirs[:, :, 300:400]
        self.identity_basis = self.shapedirs[:, :, :300]
        self.num_expression_params = 100
        self.num_identity_params = 300
        self.num_vertices = self.v_template.shape[0]
        self.num_faces = self.faces.shape[0]

        if self.weights is not None and self.J is not None:
            self.joints = self._compute_joints(self.v_template)

    def _compute_joints(self, vertices: np.ndarray) -> np.ndarray:
        if self.J is not None:
            j = self.J @ vertices
            if j.ndim == 3:
                j = j.squeeze(-1)
            return j
        return np.zeros((7, 3))

    def deform(
        self,
        expression_coeffs: np.ndarray,
        identity_coeffs: Optional[np.ndarray] = None,
        jaw_pose: Optional[np.ndarray] = None,
        eye_pose: Optional[np.ndarray] = None,
        global_pose: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        if expression_coeffs.ndim == 1:
            expression_coeffs = expression_coeffs.reshape(1, -1)

        v = self.v_template.copy()

        if identity_coeffs is not None:
            if identity_coeffs.ndim == 1:
                identity_coeffs = identity_coeffs.reshape(1, -1)
            v += np.tensordot(self.identity_basis, identity_coeffs, axes=[2, 1])

        v += np.tensordot(self.expression_basis, expression_coeffs, axes=[2, 1])

        if self.weights is not None and self.joints is not None:
            v = self._apply_linear_blend_skinning(v, jaw_pose, eye_pose, global_pose)
        elif jaw_pose is not None or global_pose is not None:
            if v.ndim == 2:
                v = v[np.newaxis, ...]
            for b in range(v.shape[0]):
                if global_pose is not None:
                    g_rot = _euler_to_rotmat(global_pose)
                    v[b] = v[b] @ g_rot.T
                if jaw_pose is not None:
                    j_rot = _euler_to_rotmat(jaw_pose)
                    jaw_joint = np.mean(v[b][[23, 24, 25]], axis=0)
                    v_centered = v[b] - jaw_joint
                    v_centered = v_centered @ j_rot.T
                    v[b] = v_centered + jaw_joint
            v = v.squeeze(0)

        if v.shape[0] == 1:
            v = v.squeeze(0)
        return v

    def _apply_linear_blend_skinning(
        self,
        vertices: np.ndarray,
        jaw_pose: Optional[np.ndarray] = None,
        eye_pose: Optional[np.ndarray] = None,
        global_pose: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        if vertices.ndim == 2:
            vertices = vertices[np.newaxis, ...]
        batch_size = vertices.shape[0]
        num_joints = self.joints.shape[0]

        all_poses = np.zeros((batch_size, num_joints * 3))
        for b in range(batch_size):
            if global_pose is not None:
                all_poses[b, 0:3] = global_pose
            if jaw_pose is not None:
                all_poses[b, 3:6] = jaw_pose
            if eye_pose is not None:
                all_poses[b, 6:12] = eye_pose

        pose_rotmats = np.zeros((batch_size, num_joints, 3, 3))
        for b in range(batch_size):
            for j in range(num_joints):
                p = all_poses[b, j*3:(j+1)*3]
                pose_rotmats[b, j] = _euler_to_rotmat(p)

        if self.posedirs is not None:
            pose_feat = np.zeros((batch_size, self.posedirs.shape[2]))
            for b in range(batch_size):
                idx = 0
                for j in range(num_joints):
                    R = pose_rotmats[b, j]
                    rr = R.flatten() - np.eye(3).flatten()
                    pose_feat[b, idx:idx+9] = rr
                    idx += 9
            v_pose = np.tensordot(self.posedirs, pose_feat, axes=[2, 1])
            if v_pose.ndim == 3:
                v_pose = v_pose.transpose(1, 0, 2)
            vertices = vertices + v_pose

        deformed = vertices.copy()
        for b in range(batch_size):
            v = vertices[b]
            j_pos = self._compute_joints(v)
            w = self.weights
            R_all = pose_rotmats[b]

            parent_indices = {}
            for child, parent in self.KINEMATIC_CHAIN:
                parent_indices[child] = parent

            transforms = np.zeros((num_joints, 4, 4))
            for j in range(num_joints):
                R = R_all[j]
                t = j_pos[j] - R @ j_pos[j]
                transforms[j, :3, :3] = R
                transforms[j, :3, 3] = t
                transforms[j, 3, 3] = 1.0

            global_transforms = np.zeros((num_joints, 4, 4))
            for j in range(num_joints):
                if parent_indices.get(j, -1) < 0:
                    global_transforms[j] = transforms[j]
                else:
                    global_transforms[j] = global_transforms[parent_indices[j]] @ transforms[j]

            rest_j = np.zeros((num_joints, 3))
            if self.J is not None:
                rest_j = self._compute_joints(self.v_template)

            final_transforms = np.zeros((num_joints, 4, 4))
            for j in range(num_joints):
                rest_t = np.eye(4)
                rest_t[:3, 3] = rest_j[j]
                final_transforms[j] = global_transforms[j] @ np.linalg.inv(rest_t)

            v_homo = np.ones((v.shape[0], 4))
            v_homo[:, :3] = v

            skinned = np.zeros_like(v)
            for j in range(num_joints):
                w_j = w[:, j:j+1]
                if w_j.shape[0] != v.shape[0]:
                    continue
                transformed = (final_transforms[j] @ v_homo.T).T[:, :3]
                skinned += w_j * transformed
            deformed[b] = skinned

        return deformed

    def deform_with_pose(
        self,
        expression_coeffs: np.ndarray,
        jaw_pose: Optional[np.ndarray] = None,
        eye_pose: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        return self.deform(expression_coeffs, jaw_pose=jaw_pose, eye_pose=eye_pose)

    def export_obj(self, vertices: np.ndarray, filepath: str) -> None:
        with open(filepath, "w") as f:
            f.write("# FLAME mesh exported from Dreamtalk\n")
            for v in vertices:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write("\n")
            for face in self.faces:
                f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")

    def visualize_pyvista(self, vertices: np.ndarray, title: str = "FLAME Mesh") -> None:
        try:
            import pyvista as pv
        except ImportError:
            raise ImportError("pyvista is required for visualization")
        pv_faces = np.hstack([np.full((self.faces.shape[0], 1), 3), self.faces]).ravel()
        mesh = pv.PolyData(vertices.astype(np.float64), pv_faces)
        plotter = pv.Plotter()
        plotter.add_mesh(mesh, color="cyan", show_edges=True, smooth_shading=True)
        plotter.camera_position = [(0, 0, 1.2), (0, 0, 0), (0, 1, 0)]
        plotter.add_text(title, font_size=12)
        plotter.show()

    def render_off_screen(self, vertices: np.ndarray, output_path: str) -> None:
        try:
            import pyvista as pv
        except ImportError:
            raise ImportError("pyvista is required for off-screen rendering")
        pv_faces = np.hstack([np.full((self.faces.shape[0], 1), 3), self.faces]).ravel()
        mesh = pv.PolyData(vertices.astype(np.float64), pv_faces)
        plotter = pv.Plotter(off_screen=True)
        plotter.add_mesh(mesh, color="cyan", show_edges=True, smooth_shading=True)
        plotter.camera_position = [(0, 0, 1.2), (0, 0, 0), (0, 1, 0)]
        plotter.show(screenshot=output_path)
        plotter.close()
