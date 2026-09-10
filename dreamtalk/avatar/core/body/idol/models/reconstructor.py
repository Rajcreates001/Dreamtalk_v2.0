# Dreamtalk - 3D Avatar Module
# Extracted from IDOL
# SapiensGS based 3D reconstructor, UV decoder, and Sapiens encoder

import os
import math
import json
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from einops import rearrange
from timm.models.vision_transformer import Block
from simple_knn._C import distCUDA2
from pytorch3d.transforms import quaternion_to_matrix, matrix_to_quaternion

from dreamtalk.avatar.core.body.idol.models.gaussian import GRenderer, get_covariance, batch_rodrigues
from dreamtalk.avatar.core.body.idol.models.smpl_x import SMPLXDeformer


class TruncExp(nn.Module):
    """Numerically stable exponential with truncated gradients."""

    @staticmethod
    def forward(x):
        exp_x = torch.exp(x)
        return exp_x


class VitHead(nn.Module):
    """ViT upsampling head: deconv -> conv -> prediction."""

    def __init__(self, in_channels=1536, out_channels=32,
                 deconv_out_channels=(512, 512, 512, 256),
                 deconv_kernel_sizes=(4, 4, 4, 4),
                 conv_out_channels=(128, 128), conv_kernel_sizes=(3, 3)):
        super().__init__()

        if deconv_out_channels:
            self.deconv_layers = self._make_deconv_layers(in_channels, deconv_out_channels, deconv_kernel_sizes)
            in_channels = deconv_out_channels[-1]
        else:
            self.deconv_layers = nn.Identity()

        if conv_out_channels:
            self.conv_layers = self._make_conv_layers(in_channels, conv_out_channels, conv_kernel_sizes)
            in_channels = conv_out_channels[-1]
        else:
            self.conv_layers = nn.Identity()

        self.cls_seg = nn.Conv2d(in_channels, out_channels, kernel_size=1)

    def _make_conv_layers(self, in_channels, layer_out_channels, layer_kernel_sizes):
        layers = []
        for out_channels, kernel_size in zip(layer_out_channels, layer_kernel_sizes):
            padding = (kernel_size - 1) // 2
            layers.append(nn.Conv2d(in_channels, out_channels, kernel_size, stride=1, padding=padding))
            layers.append(nn.InstanceNorm2d(out_channels))
            layers.append(nn.SiLU(inplace=True))
            in_channels = out_channels
        return nn.Sequential(*layers)

    def _make_deconv_layers(self, in_channels, layer_out_channels, layer_kernel_sizes):
        layers = []
        for out_channels, kernel_size in zip(layer_out_channels, layer_kernel_sizes):
            if kernel_size == 4:
                padding, output_padding = 1, 0
            elif kernel_size == 3:
                padding, output_padding = 1, 1
            elif kernel_size == 2:
                padding, output_padding = 0, 0
            else:
                raise ValueError(f"Unsupported kernel size {kernel_size}")
            layers.append(nn.ConvTranspose2d(in_channels, out_channels, kernel_size, stride=2,
                                             padding=padding, output_padding=output_padding, bias=False))
            layers.append(nn.InstanceNorm2d(out_channels))
            layers.append(nn.SiLU(inplace=True))
            in_channels = out_channels
        return nn.Sequential(*layers)

    def forward(self, inputs):
        x = self.deconv_layers(inputs)
        x = self.conv_layers(x)
        return self.cls_seg(x)


class NeckTransformer(nn.Module):
    """Skip-connected MAE decoder neck for UV feature decoding."""

    def __init__(self, patch_size=4, in_chans=32, num_patches=9216, embed_dim=1536,
                 decoder_embed_dim=1536, decoder_depth=16, decoder_num_heads=16,
                 mlp_ratio=4, norm_layer=nn.LayerNorm, total_num_hidden_states=40,
                 connect_mode="uniform"):
        super().__init__()
        self.num_patches = num_patches

        self.mask_token = nn.Parameter(torch.zeros(1, 1, decoder_embed_dim))
        self.decoder_pos_embed = nn.Parameter(
            torch.zeros(1, num_patches, decoder_embed_dim), requires_grad=True
        )

        self.decoder_blocks = nn.ModuleList([
            Block(decoder_embed_dim, decoder_num_heads, mlp_ratio, qkv_bias=True, norm_layer=norm_layer)
            for _ in range(decoder_depth)
        ])
        self.decoder_norm = norm_layer(decoder_embed_dim)
        self.decoder_pred = nn.Linear(decoder_embed_dim, patch_size**2 * in_chans, bias=True)

        if connect_mode == "uniform":
            skip = total_num_hidden_states // (decoder_depth - 1)
            self.select_hidden_states = [skip * i for i in range(decoder_depth)]
            self.select_hidden_states[-1] = total_num_hidden_states - 1
            self.select_hidden_states = self.select_hidden_states[::-1]

        self.decoder_embed = nn.ModuleList([
            nn.Linear(embed_dim, decoder_embed_dim, bias=True)
            for _ in range(decoder_depth)
        ])
        self.initialize_weights()

    def initialize_weights(self):
        decoder_pos_embed = self.get_2d_sincos_pos_embed(
            self.decoder_pos_embed.shape[-1], int(self.num_patches**0.5)
        )
        self.decoder_pos_embed.data.copy_(torch.from_numpy(decoder_pos_embed).float().unsqueeze(0))
        self.apply(self._init_weights)

    @staticmethod
    def get_2d_sincos_pos_embed(embed_dim, grid_size):
        grid_h = np.arange(grid_size, dtype=np.float32)
        grid_w = np.arange(grid_size, dtype=np.float32)
        grid = np.meshgrid(grid_w, grid_h)
        grid = np.stack(grid, axis=0).reshape([2, 1, grid_size, grid_size])
        pos_embed = NeckTransformer.get_2d_sincos_pos_embed_from_grid(embed_dim, grid)
        return pos_embed

    @staticmethod
    def get_2d_sincos_pos_embed_from_grid(embed_dim, grid):
        if embed_dim % 2 != 0:
            raise ValueError("embed_dim must be even")
        emb_h = NeckTransformer.get_1d_sincos_pos_embed_from_grid(embed_dim // 2, grid[0])
        emb_w = NeckTransformer.get_1d_sincos_pos_embed_from_grid(embed_dim // 2, grid[1])
        return np.concatenate([emb_h, emb_w], axis=1)

    @staticmethod
    def get_1d_sincos_pos_embed_from_grid(embed_dim, pos):
        if embed_dim % 2 != 0:
            raise ValueError("embed_dim must be even")
        omega = np.arange(embed_dim // 2, dtype=float)
        omega /= embed_dim / 2.0
        omega = 1.0 / 10000**omega
        pos = pos.reshape(-1)
        out = np.einsum("m,d->md", pos, omega)
        emb_sin = np.sin(out)
        emb_cos = np.cos(out)
        return np.concatenate([emb_sin, emb_cos], axis=1)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            torch.nn.init.xavier_uniform_(m.weight)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.LayerNorm):
            nn.init.constant_(m.bias, 0)
            nn.init.constant_(m.weight, 1.0)

    def forward(self, encoded_latent, ids_restore):
        B, N_l, N_f, C = encoded_latent.shape
        select_in_features = encoded_latent[:, self.select_hidden_states, :, :]
        x_list = [self.decoder_embed[i](select_in_features[:, i]) for i in range(len(self.select_hidden_states))]
        x_all_states = torch.stack(x_list)

        mask_tokens = self.mask_token.repeat(B, ids_restore.shape[1], 1)
        query_x = mask_tokens + self.decoder_pos_embed

        x = torch.zeros_like(x_all_states[0])
        x = torch.cat([x, query_x], dim=1)

        for i, blk in enumerate(self.decoder_blocks):
            x_add = x_all_states[i]
            x[:, :N_f, :] += x_add
            x = blk(x)

        x = self.decoder_norm(x)
        x = x[:, -self.num_patches:, :]
        return x


class SapiensEncoder(nn.Module):
    """Sapiens backbone encoder via TorchScript for feature extraction."""

    def __init__(self, model_path, layer_num=40, img_size=None, freeze=True):
        super().__init__()
        self.layer_num = layer_num
        self.model = torch.jit.load(model_path)
        self.freeze = freeze
        if freeze:
            self._freeze()

    def _freeze(self):
        self.model.eval()
        for param in self.model.parameters():
            param.requires_grad = False

    def forward(self, image, output_hidden_states=False):
        B = image.size(0)
        outputs = self._pretrain_forward(image, layer_num=self.layer_num, return_hidden_states=output_hidden_states)

        if output_hidden_states:
            hidden_states = torch.stack(outputs[1], 0).permute(1, 0, 2, 3)
            hidden_states = hidden_states[:, :, 1:, :]
            return hidden_states
        else:
            last_feature_map = outputs[0]
            last_feature_map = rearrange(last_feature_map, "n dim h w -> n (h w) dim")
            return last_feature_map

    def _pretrain_forward(self, inputs, layer_num, return_hidden_states=False):
        B = inputs.size(0)
        patch_embed_output, h, w, _, _ = self.model.backbone.patch_embed(inputs)
        cls_token = self.model.backbone.cls_token.expand(B, -1, -1)
        x = torch.cat([cls_token, patch_embed_output], dim=1)
        cls_pos_embed, patch_pos_embed = self.model.backbone.pos_embed[:, 0:1, :], self.model.backbone.pos_embed[:, 1:, :]

        dim = cls_pos_embed.shape[-1]
        patch_pos_embed = patch_pos_embed.reshape(-1, 64, 64, dim)
        patch_pos_embed_ = patch_pos_embed.permute(0, 3, 1, 2)
        patch_pos_embed = F.interpolate(patch_pos_embed_, size=(h, w), mode="bicubic", align_corners=False)
        patch_pos_embed = patch_pos_embed.permute(0, 2, 3, 1).view(-1, h * w, dim)
        patch_pos_embed = torch.cat([cls_pos_embed, patch_pos_embed], dim=1)

        x = x + patch_pos_embed
        x = self.model.backbone.drop_after_pos(x)

        if return_hidden_states:
            hidden_states = [x]
        for i in range(layer_num):
            x = getattr(self.model.backbone.layers, str(i))(x)
            if return_hidden_states:
                hidden_states.append(x)

        x = self.model.backbone.ln1(x)
        patch_tokens = x[:, 1:]
        output = patch_tokens.view(B, h, w, -1).permute(0, 3, 1, 2)

        if return_hidden_states:
            return output, hidden_states
        return output


class UVNDecoder(nn.Module):
    """UV-Net decoder that decodes latent codes to 3D Gaussian attributes."""

    activation_dict = {
        "relu": nn.ReLU, "silu": nn.SiLU, "softplus": nn.Softplus,
        "trunc_exp": TruncExp, "sigmoid": nn.Sigmoid,
    }

    def __init__(self, interp_mode="bilinear", base_layers=(16, 64), density_layers=(64, 1),
                 color_layers=(16, 128, 9), offset_layers=(64, 3), activation="silu",
                 sigma_activation="sigmoid", sigmoid_saturation=0.001, gender="neutral",
                 bg_color=1, image_size=(640, 896), focal=1120, is_sub2=False,
                 fix_sigma=False, reshape_type="VitHead", vithead_param=None,
                 cache_dir="work_dirs/cache"):
        super().__init__()
        self.interp_mode = interp_mode
        self.sigmoid_saturation = sigmoid_saturation
        self.deformer = SMPLXDeformer(gender, is_sub2=is_sub2, cache_dir=cache_dir)
        self.renderer = GRenderer(image_size=image_size, f=focal, bg_color=bg_color)
        self.fix_sigma = fix_sigma

        base_cache_dir = cache_dir
        if is_sub2:
            base_cache_dir = "work_dirs/cache_sub2"

        if gender == "neutral":
            select_uv = torch.as_tensor(np.load(base_cache_dir + "/init_uv_smplx_newNeutral.npy"))
            self.register_buffer("select_coord", select_uv.unsqueeze(0) * 2.0 - 1.0)
            init_pcd = torch.as_tensor(np.load(base_cache_dir + "/init_pcd_smplx_newNeutral.npy"))
            self.register_buffer("init_pcd", init_pcd.unsqueeze(0), persistent=False)
            init_rot = torch.as_tensor(np.load(base_cache_dir + "/init_rot_smplx_newNeutral.npy"))
            self.register_buffer("init_rot", init_rot, persistent=False)
            face_mask = torch.as_tensor(np.load(base_cache_dir + "/face_mask_thu_newNeutral.npy"))
            self.register_buffer("face_mask", face_mask.unsqueeze(0), persistent=False)
            hands_mask = torch.as_tensor(np.load(base_cache_dir + "/hands_mask_thu_newNeutral.npy"))
            self.register_buffer("hands_mask", hands_mask.unsqueeze(0), persistent=False)
            outside_mask = torch.as_tensor(np.load(base_cache_dir + "/outside_mask_thu_newNeutral.npy"))
            self.register_buffer("outside_mask", outside_mask.unsqueeze(0), persistent=False)

        self.num_init = self.init_pcd.shape[1]

        activation_layer = self.activation_dict[activation.lower()]

        base_net = []
        for i in range(len(base_layers) - 1):
            base_net.append(nn.Conv2d(base_layers[i], base_layers[i + 1], 3, padding=1))
            if i != len(base_layers) - 2:
                base_net.append(nn.BatchNorm2d(base_layers[i + 1]))
                base_net.append(activation_layer())
        self.base_net = nn.Sequential(*base_net)
        self.base_bn = nn.BatchNorm2d(base_layers[-1])
        self.base_activation = activation_layer()

        density_net = []
        for i in range(len(density_layers) - 1):
            density_net.append(nn.Conv2d(density_layers[i], density_layers[i + 1], 1))
            if i != len(density_layers) - 2:
                density_net.append(nn.BatchNorm2d(density_layers[i + 1]))
                density_net.append(activation_layer())
        density_net.append(self.activation_dict[sigma_activation.lower()]())
        self.density_net = nn.Sequential(*density_net)

        offset_net = []
        for i in range(len(offset_layers) - 1):
            offset_net.append(nn.Conv2d(offset_layers[i], offset_layers[i + 1], 1))
            if i != len(offset_layers) - 2:
                offset_net.append(nn.BatchNorm2d(offset_layers[i + 1]))
                offset_net.append(activation_layer())
        self.offset_net = nn.Sequential(*offset_net)

        self.dir_net = None
        color_net = []
        for i in range(len(color_layers) - 2):
            color_net.append(nn.Conv2d(color_layers[i], color_layers[i + 1], kernel_size=3, padding=1))
            color_net.append(nn.BatchNorm2d(color_layers[i + 1]))
            color_net.append(activation_layer())
        color_net.append(nn.Conv2d(color_layers[-2], color_layers[-1], kernel_size=1))
        color_net.append(nn.Sigmoid())
        self.color_net = nn.Sequential(*color_net)

        self.reshape_type = reshape_type
        if reshape_type == "VitHead":
            self.upsample_conv = VitHead(**vithead_param) if vithead_param else nn.Identity()
        elif reshape_type == "cnn":
            self.upsample_conv = nn.ConvTranspose2d(512, 32, kernel_size=4, stride=4)

        self.if_rotate_gaussian = False
        self.init_weights()

    def init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight, gain=1)
        if self.offset_net is not None:
            self.offset_net[-1].weight.data.uniform_(-1e-5, 1e-5)
            self.offset_net[-1].bias.data.zero_()

    def decode_features(self, point_code):
        """Decode UV feature map into Gaussian attributes (sigma, offset, rgb, radius, rot)."""
        if isinstance(point_code, list):
            num_scenes, _, h, w = point_code[0].shape
            geo_code, tex_code = point_code
        elif point_code.dim() == 4:
            num_scenes, n_channels, h, w = point_code.shape
            geo_code, tex_code = point_code.split(16, dim=1)
        else:
            raise ValueError(f"Unexpected point_code shape: {point_code.shape}")

        base_x = self.base_net(geo_code)
        base_x_act = self.base_activation(self.base_bn(base_x))

        sigma = self.density_net(base_x_act)
        offset = self.offset_net(base_x_act)
        color_out = self.color_net(tex_code)

        outputs = torch.cat([sigma, offset, color_out], dim=1)
        return outputs

    def sample_features(self, outputs):
        """Sample Gaussian attributes from UV feature map via grid sampling."""
        if isinstance(outputs, dict):
            outputs = outputs["output"]
        if outputs.dim() == 4:
            num_scenes, n_channels, h, w = outputs.shape
            select_coord = self.select_coord.unsqueeze(1).repeat(num_scenes, 1, 1, 1)
        else:
            raise ValueError(f"Unexpected outputs shape: {outputs.shape}")

        output_attr = F.grid_sample(outputs, select_coord, mode=self.interp_mode,
                                    padding_mode="border", align_corners=False)
        output_attr = output_attr.reshape(num_scenes, 13, -1).permute(0, 2, 1)
        sigma, offset, rgbs, radius, rot = output_attr.split([1, 3, 3, 3, 3], dim=2)

        if self.sigmoid_saturation > 0:
            rgbs = rgbs * (1 + self.sigmoid_saturation * 2) - self.sigmoid_saturation

        radius = (radius - 0.5) * 2
        rot = (rot - 0.5) * np.pi
        return sigma, rgbs, radius, rot, offset

    def extract_pcd(self, code, smpl_params, body_model, init=False, zeros_hands_off=False):
        """Extract deformed point cloud and Gaussian attributes from latent code."""
        if isinstance(code, list):
            num_scenes, _, h, w = code[0].size()
        else:
            num_scenes, _, h, w = code.size()

        init_pcd = self.init_pcd.repeat(num_scenes, 1, 1)
        sigma, rgbs, radius, rot, offset = self.sample_features(self.decode_features(code))
        if self.fix_sigma:
            sigma = torch.ones_like(sigma)
        if zeros_hands_off:
            offset[self.hands_mask[..., None].expand(num_scenes, -1, 3)] = 0

        canon_pcd = init_pcd + offset
        self.deformer.prepare_deformer(body_model, smpl_params, num_scenes, device=canon_pcd.device)
        defm_pcd, tfs = self.deformer(
            canon_pcd, rot,
            mask=(self.face_mask + self.hands_mask + self.outside_mask),
            cano=False
        )
        return defm_pcd, sigma, rgbs, offset, radius, tfs, rot

    def render_gaussians(self, xyzs, sigmas, rgbs, normals, rot, num_scenes, num_imgs, cameras, radius=None):
        """Render 3D Gaussians to 2D images."""
        assert num_scenes == 1
        pcd = xyzs.reshape(-1, 3)

        dist2 = distCUDA2(pcd)
        dist2 = torch.clamp_min(dist2, 0.0000001)
        scales = torch.sqrt(dist2)[..., None].repeat(1, 3).detach()
        scale = (radius + 1) * scales
        cov3D = get_covariance(scale, rot).reshape(-1, 6)

        images_all = []
        for i in range(num_imgs):
            self.renderer.prepare(cameras[i])
            image = self.renderer.render_gaussian(
                means3D=pcd, colors_precomp=rgbs,
                rotations=None, opacities=sigmas, scales=None, cov3D_precomp=cov3D
            )
            images_all.append(image)

        images_all = torch.stack(images_all, dim=0).unsqueeze(0).permute(0, 1, 3, 4, 2)
        return images_all

    def forward(self, code, smpl_params, body_model, cameras, num_imgs,
                init=False, zeros_hands_off=False, return_norm=False):
        """Full forward pass: decode, deform, and render."""
        num_scenes = len(code) if isinstance(code, list) else len(code)
        image = []

        xyzs, sigmas, rgbs, offsets, radius, tfs, rot = self.extract_pcd(
            code, smpl_params, body_model, init=init, zeros_hands_off=zeros_hands_off
        )

        R_delta = batch_rodrigues(rot.reshape(-1, 3))
        R = torch.bmm(self.init_rot.repeat(num_scenes, 1, 1), R_delta)
        R_def = torch.bmm(tfs.flatten(0, 1)[:, :3, :3], R)
        normals = (R_def[:, :, -1]).reshape(num_scenes, -1, 3)
        R_def_batch = R_def.reshape(num_scenes, -1, 3, 3)

        for camera_single, R_def_single, pcd_single, rgbs_single, sigmas_single, normal_single, radius_single in zip(
                cameras, R_def_batch, xyzs, rgbs, sigmas, normals, radius):
            image_single = self.render_gaussians(
                pcd_single, sigmas_single, rgbs_single, normal_single, R_def_single,
                1, num_imgs, camera_single, radius=radius_single
            )
            image.append(image_single)

        image = torch.cat(image, dim=0)
        return {"image": image}


class SapiensGSReconstructor(nn.Module):
    """Full IDOL reconstruction pipeline: Sapiens encoder + Neck + UVNDecoder."""

    def __init__(self, encoder, neck, decoder, body_model, code_activation="tanh",
                 code_reshape=(32, 96, 96), patch_size=1):
        super().__init__()
        self.encoder = encoder
        self.neck = neck
        self.decoder = decoder
        self.body_model = body_model

        self.code_reshape = code_reshape
        self.patch_size = patch_size
        self.num_patches_axis = code_reshape[-1] // patch_size
        self.num_patches = self.num_patches_axis**2
        self.code_feat_dims = code_reshape[0]
        self.code_resolution = code_reshape[-1]

        if code_activation == "tanh":
            self.code_activation = nn.Tanh()
        else:
            self.code_activation = TruncExp()

        self.ids_restore = torch.arange(0, self.num_patches).unsqueeze(0)

    def forward_image_to_uv(self, inputs_img):
        """Encode image to UV latent code."""
        features_flatten = self.encoder(inputs_img, output_hidden_states=True)

        ids_restore = self.ids_restore.to(features_flatten.device)
        uv_code = self.neck(features_flatten, ids_restore)

        batch_size, token_num, dims_feature = uv_code.shape
        feature_map = uv_code.reshape(batch_size, self.num_patches_axis, self.num_patches_axis,
                                       self.code_feat_dims, self.patch_size, self.patch_size)
        feature_map = feature_map.permute(0, 3, 1, 4, 2, 5)
        feature_map = feature_map.reshape(batch_size, self.code_feat_dims,
                                           self.code_resolution, self.code_resolution)
        code = self.code_activation(feature_map)
        return code

    def forward(self, image, smpl_params, cameras, num_imgs, zeros_hands_off=False):
        """Full forward pass: image -> UV code -> 3D Gaussians -> rendered image."""
        with torch.no_grad():
            code = self.forward_image_to_uv(image)

        with torch.no_grad():
            output_list = []
            total_frames = min(smpl_params.shape[0], 300)
            res_uv = None

            for i in range(0, total_frames, 5):
                num_imgs_batch = min(5, total_frames - i)
                code_bt = code.expand(num_imgs_batch, -1, -1, -1)
                cameras_bt = cameras[i:i + num_imgs_batch]

                res_uv = self.decoder.decode_features(code_bt)
                sigma, rgbs, radius, rot, offset = self.decoder.sample_features(res_uv)
                code_features = [sigma, rgbs, radius, rot, offset]

                res_def_points = self.decoder.extract_pcd(
                    code_bt, smpl_params[i:i + num_imgs_batch].to(code_bt.dtype),
                    self.body_model, zeros_hands_off=zeros_hands_off
                )
                output = self.decoder.render_gaussians(
                    res_def_points[0], res_def_points[1], res_def_points[2],
                    None, res_def_points[5], 1, 1, cameras_bt.to(code_bt.dtype),
                    radius=res_def_points[4]
                )
                image_out = output[:, 0].cpu().to(torch.float32)
                output_list.append(image_out)

            output = torch.cat(output_list, 0)
            frames = rearrange(output, "b h w c -> b c h w")
        return frames
