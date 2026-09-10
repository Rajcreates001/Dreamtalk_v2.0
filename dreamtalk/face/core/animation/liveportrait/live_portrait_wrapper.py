# Dreamtalk - Face Engine
# Extracted from LivePortrait
import contextlib
import os.path as osp
import numpy as np
import cv2
import torch
import yaml

from .utils.timer import Timer
from .utils.helper import load_model, concat_feat
from .utils.camera import headpose_pred_to_degree, get_rotation_matrix
from .utils.retargeting_utils import calc_eye_close_ratio, calc_lip_close_ratio
from .config.inference_config import InferenceConfig
from .utils.rprint import rlog as log


class LivePortraitWrapper(object):
    def __init__(self, inference_cfg: InferenceConfig):
        self.inference_cfg = inference_cfg
        self.device_id = inference_cfg.device_id
        self.compile = inference_cfg.flag_do_torch_compile
        if inference_cfg.flag_force_cpu:
            self.device = 'cpu'
        else:
            try:
                if torch.backends.mps.is_available():
                    self.device = 'mps'
                else:
                    self.device = 'cuda:' + str(self.device_id)
            except:
                self.device = 'cuda:' + str(self.device_id)

        model_config = yaml.load(open(inference_cfg.models_config, 'r'), Loader=yaml.SafeLoader)
        self.appearance_feature_extractor = load_model(inference_cfg.checkpoint_F, model_config, self.device, 'appearance_feature_extractor')
        log(f'Load appearance_feature_extractor from {osp.realpath(inference_cfg.checkpoint_F)} done.')
        self.motion_extractor = load_model(inference_cfg.checkpoint_M, model_config, self.device, 'motion_extractor')
        log(f'Load motion_extractor from {osp.realpath(inference_cfg.checkpoint_M)} done.')
        self.warping_module = load_model(inference_cfg.checkpoint_W, model_config, self.device, 'warping_module')
        log(f'Load warping_module from {osp.realpath(inference_cfg.checkpoint_W)} done.')
        self.spade_generator = load_model(inference_cfg.checkpoint_G, model_config, self.device, 'spade_generator')
        log(f'Load spade_generator from {osp.realpath(inference_cfg.checkpoint_G)} done.')

        # Load stitching/retargeting module if the checkpoint is a .pth file (landmark.onnx is for face detection, not stitching)
        if (inference_cfg.checkpoint_S is not None
                and osp.exists(inference_cfg.checkpoint_S)
                and inference_cfg.checkpoint_S.endswith('.pth')):
            self.stitching_retargeting_module = load_model(inference_cfg.checkpoint_S, model_config, self.device, 'stitching_retargeting_module')
            log(f'Load stitching_retargeting_module from {osp.realpath(inference_cfg.checkpoint_S)} done.')
        else:
            self.stitching_retargeting_module = None

        if self.compile:
            torch._dynamo.config.suppress_errors = True
            self.warping_module = torch.compile(self.warping_module, mode='max-autotune')
            self.spade_generator = torch.compile(self.spade_generator, mode='max-autotune')

        self.timer = Timer()

    def inference_ctx(self):
        if self.device == "mps":
            ctx = contextlib.nullcontext()
        else:
            ctx = torch.autocast(device_type=self.device[:4], dtype=torch.float16,
                                 enabled=self.inference_cfg.flag_use_half_precision)
        return ctx

    def update_config(self, user_args):
        for k, v in user_args.items():
            if hasattr(self.inference_cfg, k):
                setattr(self.inference_cfg, k, v)

    def prepare_source(self, img: np.ndarray) -> torch.Tensor:
        h, w = img.shape[:2]
        if h != self.inference_cfg.input_shape[0] or w != self.inference_cfg.input_shape[1]:
            x = cv2.resize(img, (self.inference_cfg.input_shape[0], self.inference_cfg.input_shape[1]))
        else:
            x = img.copy()
        if x.ndim == 3:
            x = x[np.newaxis].astype(np.float32) / 255.
        elif x.ndim == 4:
            x = x.astype(np.float32) / 255.
        else:
            raise ValueError(f'img ndim should be 3 or 4: {x.ndim}')
        x = np.clip(x, 0, 1)
        x = torch.from_numpy(x).permute(0, 3, 1, 2)
        x = x.to(self.device)
        return x

    def prepare_videos(self, imgs) -> torch.Tensor:
        if isinstance(imgs, list):
            _imgs = np.array(imgs)[..., np.newaxis]
        elif isinstance(imgs, np.ndarray):
            _imgs = imgs
        else:
            raise ValueError(f'imgs type error: {type(imgs)}')
        y = _imgs.astype(np.float32) / 255.
        y = np.clip(y, 0, 1)
        y = torch.from_numpy(y).permute(0, 4, 3, 1, 2)
        y = y.to(self.device)
        return y

    def extract_feature_3d(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad(), self.inference_ctx():
            feature_3d = self.appearance_feature_extractor(x)
        return feature_3d.float()

    def get_kp_info(self, x: torch.Tensor, **kwargs) -> dict:
        with torch.no_grad(), self.inference_ctx():
            kp_info = self.motion_extractor(x)
            if self.inference_cfg.flag_use_half_precision:
                for k, v in kp_info.items():
                    if isinstance(v, torch.Tensor):
                        kp_info[k] = v.float()
        flag_refine_info: bool = kwargs.get('flag_refine_info', True)
        if flag_refine_info:
            bs = kp_info['kp'].shape[0]
            kp_info['pitch'] = headpose_pred_to_degree(kp_info['pitch'])[:, None]
            kp_info['yaw'] = headpose_pred_to_degree(kp_info['yaw'])[:, None]
            kp_info['roll'] = headpose_pred_to_degree(kp_info['roll'])[:, None]
            kp_info['kp'] = kp_info['kp'].reshape(bs, -1, 3)
            kp_info['exp'] = kp_info['exp'].reshape(bs, -1, 3)
        return kp_info

    def get_pose_dct(self, kp_info: dict) -> dict:
        pose_dct = dict(
            pitch=headpose_pred_to_degree(kp_info['pitch']).item(),
            yaw=headpose_pred_to_degree(kp_info['yaw']).item(),
            roll=headpose_pred_to_degree(kp_info['roll']).item(),
        )
        return pose_dct

    def get_fs_and_kp_info(self, source_prepared, driving_first_frame):
        source_kp_info = self.get_kp_info(source_prepared, flag_refine_info=True)
        source_rotation = get_rotation_matrix(source_kp_info['pitch'], source_kp_info['yaw'], source_kp_info['roll'])
        driving_first_frame_kp_info = self.get_kp_info(driving_first_frame, flag_refine_info=True)
        driving_first_frame_rotation = get_rotation_matrix(
            driving_first_frame_kp_info['pitch'],
            driving_first_frame_kp_info['yaw'],
            driving_first_frame_kp_info['roll']
        )
        source_feature_3d = self.extract_feature_3d(source_prepared)
        return source_kp_info, source_rotation, source_feature_3d, driving_first_frame_kp_info, driving_first_frame_rotation

    def transform_keypoint(self, kp_info: dict):
        kp = kp_info['kp']
        pitch, yaw, roll = kp_info['pitch'], kp_info['yaw'], kp_info['roll']
        t, exp = kp_info['t'], kp_info['exp']
        scale = kp_info['scale']

        pitch = headpose_pred_to_degree(pitch)
        yaw = headpose_pred_to_degree(yaw)
        roll = headpose_pred_to_degree(roll)

        bs = kp.shape[0]
        if kp.ndim == 2:
            num_kp = kp.shape[1] // 3
        else:
            num_kp = kp.shape[1]

        rot_mat = get_rotation_matrix(pitch, yaw, roll)
        kp_transformed = kp.view(bs, num_kp, 3) @ rot_mat + exp.view(bs, num_kp, 3)
        kp_transformed *= scale[..., None]
        kp_transformed[:, :, 0:2] += t[:, None, 0:2]
        return kp_transformed

    def retarget_eye(self, kp_source: torch.Tensor, eye_close_ratio: torch.Tensor) -> torch.Tensor:
        feat_eye = concat_feat(kp_source, eye_close_ratio)
        with torch.no_grad():
            delta = self.stitching_retargeting_module['eye'](feat_eye)
        return delta.reshape(-1, kp_source.shape[1], 3)

    def retarget_lip(self, kp_source: torch.Tensor, lip_close_ratio: torch.Tensor) -> torch.Tensor:
        feat_lip = concat_feat(kp_source, lip_close_ratio)
        with torch.no_grad():
            delta = self.stitching_retargeting_module['lip'](feat_lip)
        return delta.reshape(-1, kp_source.shape[1], 3)

    def stitch(self, kp_source: torch.Tensor, kp_driving: torch.Tensor) -> torch.Tensor:
        feat_stiching = concat_feat(kp_source, kp_driving)
        with torch.no_grad():
            delta = self.stitching_retargeting_module['stitching'](feat_stiching)
        return delta

    def stitching(self, kp_source: torch.Tensor, kp_driving: torch.Tensor) -> torch.Tensor:
        if self.stitching_retargeting_module is not None:
            bs, num_kp = kp_source.shape[:2]
            kp_driving_new = kp_driving.clone()
            delta = self.stitch(kp_source, kp_driving_new)
            delta_exp = delta[..., :3 * num_kp].reshape(bs, num_kp, 3)
            delta_tx_ty = delta[..., 3 * num_kp:3 * num_kp + 2].reshape(bs, 1, 2)
            kp_driving_new += delta_exp
            kp_driving_new[..., :2] += delta_tx_ty
            return kp_driving_new
        return kp_driving

    def warp_decode(self, feature_3d: torch.Tensor, kp_source: torch.Tensor, kp_driving: torch.Tensor) -> torch.Tensor:
        with torch.no_grad(), self.inference_ctx():
            if self.compile:
                torch.compiler.cudagraph_mark_step_begin()
            ret_dct = self.warping_module(feature_3d, kp_source=kp_source, kp_driving=kp_driving)
            ret_dct['out'] = self.spade_generator(feature=ret_dct['out'])
            if self.inference_cfg.flag_use_half_precision:
                for k, v in ret_dct.items():
                    if isinstance(v, torch.Tensor):
                        ret_dct[k] = v.float()
        return ret_dct

    def parse_output(self, out: torch.Tensor) -> np.ndarray:
        out = np.transpose(out.data.cpu().numpy(), [0, 2, 3, 1])
        out = np.clip(out, 0, 1)
        out = np.clip(out * 255, 0, 255).astype(np.uint8)
        return out

    def calc_ratio(self, lmk_lst):
        input_eye_ratio_lst = []
        input_lip_ratio_lst = []
        for lmk in lmk_lst:
            input_eye_ratio_lst.append(calc_eye_close_ratio(lmk[None]))
            input_lip_ratio_lst.append(calc_lip_close_ratio(lmk[None]))
        return input_eye_ratio_lst, input_lip_ratio_lst

    def calc_combined_eye_ratio(self, c_d_eyes_i, source_lmk):
        c_s_eyes = calc_eye_close_ratio(source_lmk[None])
        c_s_eyes_tensor = torch.from_numpy(c_s_eyes).float().to(self.device)
        c_d_eyes_i_tensor = torch.Tensor([c_d_eyes_i[0][0]]).reshape(1, 1).to(self.device)
        combined_eye_ratio_tensor = torch.cat([c_s_eyes_tensor, c_d_eyes_i_tensor], dim=1)
        return combined_eye_ratio_tensor

    def calc_combined_lip_ratio(self, c_d_lip_i, source_lmk):
        c_s_lip = calc_lip_close_ratio(source_lmk[None])
        c_s_lip_tensor = torch.from_numpy(c_s_lip).float().to(self.device)
        c_d_lip_i_tensor = torch.Tensor([c_d_lip_i[0]]).to(self.device).reshape(1, 1)
        combined_lip_ratio_tensor = torch.cat([c_s_lip_tensor, c_d_lip_i_tensor], dim=1)
        return combined_lip_ratio_tensor
