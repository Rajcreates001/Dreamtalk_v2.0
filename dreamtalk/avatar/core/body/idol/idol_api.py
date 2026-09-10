# Dreamtalk - 3D Avatar Module
# Extracted from IDOL
# High-level inference wrapper for single-image 3D reconstruction

import os
import torch
import json
import numpy as np
from tqdm import tqdm
from einops import rearrange

from dreamtalk.avatar.core.body.idol.config import IDOLConfig
from dreamtalk.avatar.core.body.idol.inference import (
    load_image, load_smplx_from_npy, load_smplx_from_json, load_smplify_json,
    prepare_camera, construct_camera, construct_camera_from_motionx,
    reset_first_frame_rotation, add_root_rotate_to_smplx,
    get_image_dimensions, save_video, get_name_str,
)
from dreamtalk.avatar.core.body.idol.models.reconstructor import (
    SapiensGSReconstructor, SapiensEncoder, NeckTransformer, UVNDecoder,
)


class IDOLInference:
    """High-level wrapper for IDOL single-image to 3D avatar reconstruction."""

    def __init__(self, config: IDOLConfig = None, device: torch.device = None):
        self.config = config or IDOLConfig()
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.body_model = None

    def build_model(self):
        """Build the SapiensGS reconstruction model from config."""
        encoder = SapiensEncoder(
            model_path=self.config.encoder_model_path,
            layer_num=40,
            freeze=True,
        )

        neck = NeckTransformer(
            patch_size=4, in_chans=32, num_patches=9216,
            embed_dim=1536, decoder_embed_dim=1536,
            decoder_depth=16, decoder_num_heads=16,
            total_num_hidden_states=40,
        )

        decoder = UVNDecoder(
            interp_mode="bilinear",
            base_layers=[16, 64],
            density_layers=[64, 1],
            color_layers=[16, 128, 9],
            offset_layers=[64, 3],
            activation="silu",
            bg_color=1,
            sigma_activation="sigmoid",
            gender=self.config.gender,
            is_sub2=True,
            image_size=self.config.image_size,
            focal=1120,
            fix_sigma=True,
            reshape_type="VitHead",
            vithead_param={
                "in_channels": 1536,
                "out_channels": 32,
                "deconv_out_channels": [512, 512, 512, 256],
                "deconv_kernel_sizes": [4, 4, 4, 4],
                "conv_out_channels": [128, 128],
                "conv_kernel_sizes": [3, 3],
            },
            cache_dir=self.config.cache_dir,
        )

        body_model = self._load_body_model()

        self.model = SapiensGSReconstructor(
            encoder=encoder, neck=neck, decoder=decoder,
            body_model=body_model,
            code_reshape=[32, 96, 96],
            patch_size=1,
        ).to(self.device).eval()

        return self.model

    def _load_body_model(self):
        """Load SMPL-X body model."""
        try:
            from smplx import SMPLX as SMPLXModel
            body_model = SMPLXModel(
                model_path="lib/models/deformers/smplx/SMPLX",
                gender=self.config.gender,
                create_body_pose=False, create_betas=False,
                create_global_orient=False, create_transl=False,
                create_expression=False, create_jaw_pose=False,
                create_leye_pose=False, create_reye_pose=False,
                create_right_hand_pose=False, create_left_hand_pose=False,
                use_pca=True, num_pca_comps=12, num_betas=10,
                flat_hand_mean=False, ext="pkl",
            )
            return body_model
        except ImportError:
            raise ImportError("SMPL-X library required. Install with: pip install smplx")

    def load_checkpoint(self, checkpoint_path):
        """Load model weights from checkpoint."""
        if self.model is None:
            self.build_model()
        state_dict = torch.load(checkpoint_path, map_location=self.device)
        if "state_dict" in state_dict:
            state_dict = state_dict["state_dict"]
        self.model.load_state_dict(state_dict, strict=False)
        return self

    def reconstruct_from_image(self, image_path, smplx_ref_path, smplx_driven_path,
                               render_mode="novel_pose", output_dir="outputs"):
        """Full pipeline: reconstruct from single image and animate with SMPL-X.

        Args:
            image_path: Path to input image
            smplx_ref_path: Path to reference SMPL-X JSON (for betas)
            smplx_driven_path: Path to driving SMPL-X sequence (.npy or .json)
            render_mode: One of "novel_pose", "reconstruct", "novel_pose_A"
            output_dir: Output directory

        Returns:
            frames: Rendered video frames as torch.Tensor
        """
        if self.model is None:
            self.build_model()

        os.makedirs(output_dir, exist_ok=True)

        # Load reference SMPL-X for betas
        with open(smplx_ref_path) as f:
            smplx_ref = json.load(f)
        betas = smplx_ref.get("shapes", smplx_ref.get("betas_save"))

        smpl_params = torch.zeros(1, 189).to(self.device)
        smpl_params[:, 70:80] = torch.Tensor(betas).to(self.device)

        # Load driving SMPL-X sequence
        if render_mode == "novel_pose":
            if smplx_driven_path.endswith(".npy"):
                driven_params = load_smplx_from_npy(smplx_driven_path, self.device)
                driven_params[:, 70:80] = torch.Tensor(betas).to(self.device)
                if self.config.use_uniform_coordinates:
                    root_orient = driven_params[:, 4:7]
                    trans = driven_params[:, 1:4]
                    new_root, new_trans = reset_first_frame_rotation(root_orient, trans)
                    driven_params[:, 4:7] = new_root
                    driven_params[:, 1:4] = new_trans.squeeze()
            elif smplx_driven_path.endswith(".json"):
                driven_params = load_smplx_from_json(smplx_driven_path, self.device)
                driven_params[:, 70:80] = torch.Tensor(betas).to(self.device)
        elif render_mode == "reconstruct":
            RT_rec, intri_rec, _ = load_smplify_json(smplx_ref_path)
            H, W = get_image_dimensions(image_path)
            driven_params = add_root_rotate_to_smplx(smpl_params.clone(), 180, self.device)
            driven_params[:, 70:80] = torch.Tensor(betas).to(self.device)
        elif render_mode == "novel_pose_A":
            driven_params = add_root_rotate_to_smplx(smpl_params.clone(), 180, self.device)
            driven_params[:, 70:80] = torch.Tensor(betas).to(self.device)

        # Load input image
        image = load_image(image_path, output_dir, remove_bg=self.config.remove_bg)
        image = image.unsqueeze(0).to(self.device)

        # Prepare cameras
        total_frames = min(driven_params.shape[0], 300)
        K, cam_list = prepare_camera(resolution_x=896, resolution_y=640,
                                      num_views=total_frames)
        cameras = construct_camera(K, cam_list, self.device)
        cameras = cameras[0:1].repeat(total_frames, 1)
        cameras = cameras[:, None, :]

        # Reconstruct
        with torch.no_grad():
            code = self.model.forward_image_to_uv(image)

        # Animate and render
        output_list = []
        batch_size = self.config.batch_size
        with torch.no_grad():
            for i in tqdm(range(0, total_frames, batch_size)):
                end = min(i + batch_size, total_frames)
                code_bt = code.expand(end - i, -1, -1, -1)
                cameras_bt = cameras[i:end]
                smpl_batch = driven_params[i:end].to(code_bt.dtype)

                res_uv = self.model.decoder.decode_features(code_bt)
                sigma, rgbs, radius, rot, offset = self.model.decoder.sample_features(res_uv)

                res_def = self.model.decoder.extract_pcd(
                    code_bt, smpl_batch, self.body_model,
                    zeros_hands_off=self.config.use_hands_zero_offset
                )

                output = self.model.decoder.render_gaussians(
                    res_def[0], res_def[1], res_def[2], None, res_def[5],
                    1, 1, cameras_bt.to(code_bt.dtype), radius=res_def[4]
                )
                output_list.append(output[:, 0].cpu().to(torch.float32))

        frames = rearrange(torch.cat(output_list, 0), "b h w c -> b c h w")
        video_path = os.path.join(output_dir, "output.mp4")
        save_video(frames[:, :4, ...].to(torch.float32), video_path)
        return frames

    def reconstruct_only(self, image_path, smplx_ref_path, output_dir="outputs"):
        """Reconstruct 3D avatar only (no animation)."""
        return self.reconstruct_from_image(
            image_path, smplx_ref_path, smplx_ref_path,
            render_mode="reconstruct", output_dir=output_dir
        )
