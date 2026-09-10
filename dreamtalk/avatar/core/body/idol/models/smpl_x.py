# Dreamtalk - 3D Avatar Module
# Extracted from IDOL
# Original deformer from AG3D, modified for Dreamtalk

import torch
import numpy as np
from pytorch3d import ops

from dreamtalk.avatar.core.body.idol.models.gaussian import batch_rodrigues


class SMPLXDeformer(torch.nn.Module):
    """SMPL-X deformer for 3D Gaussian skinning and deformation."""

    def __init__(self, gender="neutral", is_sub2=False, cache_dir="work_dirs/cache"):
        super().__init__()
        self.gender = gender
        base_cache_dir = cache_dir
        if is_sub2:
            base_cache_dir = "work_dirs/cache_sub2"

        if gender == "neutral":
            init_spdir = torch.as_tensor(np.load(base_cache_dir + "/init_spdir_smplx_thu_newNeutral.npy"))
            self.register_buffer("init_spdir", init_spdir, persistent=False)
            init_podir = torch.as_tensor(np.load(base_cache_dir + "/init_podir_smplx_thu_newNeutral.npy"))
            self.register_buffer("init_podir", init_podir, persistent=False)
            init_lbsw = torch.as_tensor(np.load(base_cache_dir + "/init_lbsw_smplx_thu_newNeutral.npy"))
            self.register_buffer("init_lbsw", init_lbsw.unsqueeze(0), persistent=False)
            init_faces = torch.as_tensor(np.load(base_cache_dir + "/init_faces_smplx_newNeutral.npy"))
            self.register_buffer("init_faces", init_faces.unsqueeze(0), persistent=False)
        elif gender == "male":
            init_spdir = torch.as_tensor(np.load(base_cache_dir + "/init_spdir_smplx_thu_newMale.npy"))
            self.register_buffer("init_spdir", init_spdir, persistent=False)
            init_podir = torch.as_tensor(np.load(base_cache_dir + "/init_podir_smplx_thu_newMale.npy"))
            self.register_buffer("init_podir", init_podir, persistent=False)
            init_lbsw = torch.as_tensor(np.load(base_cache_dir + "/init_lbsw_smplx_thu_newMale.npy"))
            self.register_buffer("init_lbsw", init_lbsw.unsqueeze(0), persistent=False)
            init_faces = torch.as_tensor(np.load(base_cache_dir + "/init_faces_smplx_neuMale.npy"))
            self.register_buffer("init_faces", init_faces.unsqueeze(0), persistent=False)

        self.initialized = False

    def initialize(self, body_model, poses, lbs_weights):
        """Initialize LBS volume and canonical space."""
        batch_size = 1
        device = body_model.posedirs.device
        body_pose_t = torch.zeros((batch_size, 63)).to(device)
        jaw_pose_t = torch.zeros((batch_size, 3)).to(device)
        left_hand_pose_t = torch.tensor([1.4624, -0.1615, 0.1361, 1.3851, -0.2597, 0.0247, -0.0683, -0.4478,
                                         -0.6652, -0.7290, 0.0084, -0.4818]).unsqueeze(0).to(device)
        right_hand_pose_t = left_hand_pose_t.clone()
        leye_pose_t = torch.zeros((batch_size, 3)).to(device)
        reye_pose_t = torch.zeros((batch_size, 3)).to(device)
        expression_t = torch.zeros((batch_size, 10)).to(device)
        global_orient = torch.zeros((batch_size, 3)).to(device)
        betas = torch.zeros((batch_size, 10)).to(device)

        smpl_outputs = body_model(
            betas=betas, body_pose=body_pose_t, jaw_pose=jaw_pose_t,
            left_hand_pose=left_hand_pose_t, right_hand_pose=right_hand_pose_t,
            leye_pose=leye_pose_t, reye_pose=reye_pose_t, expression=expression_t,
            transl=None, global_orient=global_orient
        )

        tfs_inv_t = torch.inverse(smpl_outputs.A.float().detach())
        vs_template = smpl_outputs.vertices
        smpl_faces = torch.as_tensor(body_model.faces.astype(np.int64))

        pose_offset_cano = torch.matmul(smpl_outputs.pose_feature, self.init_podir).reshape(1, -1, 3)
        pose_offset_cano = torch.cat([pose_offset_cano[:, self.init_faces[..., i]] for i in range(3)], dim=1).mean(1)

        self.register_buffer("tfs_inv_t", tfs_inv_t, persistent=False)
        self.register_buffer("vs_template", vs_template, persistent=False)
        self.register_buffer("smpl_faces", smpl_faces, persistent=False)
        self.register_buffer("pose_offset_cano", pose_offset_cano, persistent=False)
        self.initialized = True

    def prepare_deformer(self, body_model, smpl_params=None, num_scenes=1, device=None, if_use_pca=True):
        """Prepare deformation parameters from SMPL-X params."""
        if smpl_params is None:
            smpl_params_dict = {
                "betas": torch.zeros((num_scenes, 10)).to(device),
                "expression": torch.zeros((num_scenes, 10)).to(device),
                "body_pose": torch.zeros((num_scenes, 63)).to(device),
                "left_hand_pose": torch.tensor([1.4624, -0.1615, 0.1361, 1.3851, -0.2597, 0.0247, -0.0683, -0.4478,
                                                -0.6652, -0.7290, 0.0084, -0.4818]).unsqueeze(0).to(device).repeat(num_scenes, 1),
                "right_hand_pose": torch.tensor([1.4624, -0.1615, 0.1361, 1.3851, -0.2597, 0.0247, -0.0683, -0.4478,
                                                 -0.6652, -0.7290, 0.0084, -0.4818]).unsqueeze(0).to(device).repeat(num_scenes, 1),
                "jaw_pose": torch.zeros((num_scenes, 3)).to(device),
                "leye_pose": torch.zeros((num_scenes, 3)).to(device),
                "reye_pose": torch.zeros((num_scenes, 3)).to(device),
                "global_orient": torch.zeros((num_scenes, 3)).to(device),
                "transl": None,
                "scale": None,
            }
        else:
            batchsize = smpl_params.shape[0]
            scale, transl, global_orient, pose, betas, left_hand_pose, right_hand_pose, jaw_pose, leye_pose, reye_pose, expression = torch.split(
                smpl_params, [1, 3, 3, 63, 10, 45 if not if_use_pca else 12, 45 if not if_use_pca else 12, 3, 3, 3, 10], dim=1
            )
            smpl_params_dict = {
                "betas": betas.reshape(-1, 10),
                "expression": expression.reshape(-1, 10),
                "body_pose": pose.reshape(-1, 63),
                "left_hand_pose": left_hand_pose.reshape(batchsize, -1),
                "right_hand_pose": right_hand_pose.reshape(batchsize, -1),
                "jaw_pose": jaw_pose.reshape(-1, 3),
                "leye_pose": leye_pose.reshape(-1, 3),
                "reye_pose": reye_pose.reshape(-1, 3),
                "global_orient": global_orient.reshape(-1, 3),
                "transl": transl.reshape(-1, 3),
                "scale": scale.reshape(-1, 1),
            }

        device = smpl_params_dict["betas"].device
        smpl_outputs = body_model(**smpl_params_dict, use_pca=if_use_pca)

        self.smpl_outputs = smpl_outputs
        tfs = (smpl_outputs.A) @ self.tfs_inv_t.expand(smpl_outputs.A.shape[0], -1, -1, -1)
        self.tfs = tfs
        self.tfs_A = smpl_outputs.A
        self.shape_offset = torch.einsum("bl,mkl->bmk", [smpl_outputs.betas, self.init_spdir])
        self.pose_offset = torch.matmul(smpl_outputs.pose_feature, self.init_podir).reshape(self.shape_offset.shape)

    def forward(self, pts_in, rot_in, mask=None, cano=True):
        """Skinning: deform canonical points to posed space."""
        pts = pts_in.clone()
        if cano:
            return pts, None

        b, n, _ = pts.shape
        init_faces = self.init_faces

        shape_offset = torch.cat([self.shape_offset[:, init_faces[..., i]] for i in range(3)], dim=1).mean(1)
        pose_offset = torch.cat([self.pose_offset[:, init_faces[..., i]] for i in range(3)], dim=1).mean(1)

        pts_query_lbs = pts.detach()
        lbs_weights = self._lbs_skin(pts_query_lbs)
        pts_cano_all, w_tf = self._apply_skinning(
            pts, shape_offset, pose_offset, lbs_weights, mask
        )

        pts_cano_all = pts_cano_all.reshape(b, n, -1, 3)
        return pts_cano_all, w_tf.clone()

    def _lbs_skin(self, pts):
        """Compute LBS weights for arbitrary points via voxelized field."""
        weights = self.init_lbsw.expand(pts.shape[0], -1, -1)
        return weights

    def _apply_skinning(self, pts, shape_offset, pose_offset, lbs_weights, mask):
        """Apply linear blend skinning."""
        if mask is not None:
            from pytorch3d import ops
            k = 1
            dist_sq, idx, _ = ops.knn_points(
                pts, self.smpl_outputs.vertices.float().expand(pts.shape[0], -1, -1), K=k, return_nn=True
            )
            dist = dist_sq.sqrt().clamp_(0.00003, 0.1)
            weights = self.init_lbsw[0][idx]
            ws = 1.0 / dist
            ws = ws / ws.sum(-1, keepdim=True)
            weights = (ws[..., None] * weights).sum(2).detach()
            lbs_weights = weights

        pts_offset = pts + shape_offset + pose_offset
        b, n, _ = pts_offset.shape
        tfs = self.tfs_A
        tfs_inv = self.tfs_inv_t

        rest_joints = self.smpl_outputs.Jtr
        posed_joints = tfs[:, :, :3, 3]
        weights_exp = lbs_weights.unsqueeze(-1).unsqueeze(-1)

        identity_mat = torch.eye(3, device=pts.device).expand(b, n, 3, 3)
        rot_mats = tfs[:, :, :3, :3]
        trans = posed_joints.unsqueeze(1)

        w_rot = (weights_exp * rot_mats.unsqueeze(1)).sum(dim=2)
        w_trans = (weights_exp * trans.unsqueeze(1)).sum(dim=2)

        deformed = torch.bmm(w_rot, pts_offset.unsqueeze(-1)).squeeze(-1) + w_trans.squeeze(-2)
        w_tf = torch.cat([w_rot, w_trans], dim=-1)

        return deformed, w_tf

    def parse_smpl_params(self, smpl_params, if_use_pca=True):
        """Parse flat SMPL-X parameters into dictionary."""
        if smpl_params.shape[1] == 189:
            scale, transl, global_orient, pose, betas, left_hand_pose, right_hand_pose, jaw_pose, leye_pose, reye_pose, expression = torch.split(
                smpl_params, [1, 3, 3, 63, 10, 45, 45, 3, 3, 3, 10], dim=1
            )
            if_use_pca = False
        else:
            scale, transl, global_orient, pose, betas, left_hand_pose, right_hand_pose, jaw_pose, leye_pose, reye_pose, expression = torch.split(
                smpl_params, [1, 3, 3, 63, 10, 12, 12, 3, 3, 3, 10], dim=1
            )
        return {
            "betas": betas.reshape(-1, 10),
            "expression": expression.reshape(-1, 10),
            "body_pose": pose.reshape(-1, 63),
            "left_hand_pose": left_hand_pose,
            "right_hand_pose": right_hand_pose,
            "jaw_pose": jaw_pose.reshape(-1, 3),
            "leye_pose": leye_pose.reshape(-1, 3),
            "reye_pose": reye_pose.reshape(-1, 3),
            "global_orient": global_orient.reshape(-1, 3),
            "transl": transl.reshape(-1, 3),
            "scale": scale.reshape(-1, 1),
        }, if_use_pca
