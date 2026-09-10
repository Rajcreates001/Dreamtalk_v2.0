# Dreamtalk - Face Engine
# Extracted from LivePortrait
import os
import os.path as osp
import torch
import numpy as np


def basename(fn):
    return osp.splitext(osp.basename(fn))[0]


def mkdir(d):
    os.makedirs(d, exist_ok=True)


def is_image(fn):
    ext = osp.splitext(fn)[1].lower()
    return ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']


def is_video(fn):
    ext = osp.splitext(fn)[1].lower()
    return ext in ['.mp4', '.avi', '.mov', '.flv', '.mkv', '.webm']


def is_template(fn):
    ext = osp.splitext(fn)[1].lower()
    return ext == '.pkl'


def remove_suffix(fn):
    return osp.splitext(fn)[0]


def is_square_video(fn):
    import cv2
    cap = cv2.VideoCapture(fn)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return w == h


def dct2device(dct, device):
    for k, v in dct.items():
        if isinstance(v, np.ndarray):
            dct[k] = torch.from_numpy(v).to(device)
        elif isinstance(v, torch.Tensor):
            dct[k] = v.to(device)
    return dct


def load_model(cp, model_config, device, model_type):
    import yaml
    from dreamtalk.face.core.animation.liveportrait.modules.appearance_feature_extractor import AppearanceFeatureExtractor
    from dreamtalk.face.core.animation.liveportrait.modules.motion_extractor import MotionExtractor
    from dreamtalk.face.core.animation.liveportrait.modules.warping_network import WarpingNetwork
    from dreamtalk.face.core.animation.liveportrait.modules.spade_generator import SPADEDecoder
    from dreamtalk.face.core.animation.liveportrait.modules.stitching_retargeting_network import StitchingRetargetingNetwork

    model_type_to_class = {
        'appearance_feature_extractor': AppearanceFeatureExtractor,
        'motion_extractor': MotionExtractor,
        'warping_module': WarpingNetwork,
        'spade_generator': SPADEDecoder,
    }

    if model_type in model_type_to_class:
        model_cfg = model_config[model_type]
        model_class = model_type_to_class[model_type]
        model = model_class(**model_cfg)
        state_dict = torch.load(cp, map_location=lambda storage, loc: storage, weights_only=False)
        model.load_state_dict(state_dict)
        model = model.to(device)
        model.eval()
        return model
    elif model_type == 'stitching_retargeting_module':
        # Special handling for stitching+retargeting
        model_cfg = model_config[model_type]
        ret = {}
        for key, sub_cfg in model_cfg.items():
            sub_net = StitchingRetargetingNetwork(**sub_cfg)
            ret[key] = sub_net.to(device)
        state_dict = torch.load(cp, map_location=lambda storage, loc: storage, weights_only=False)
        for key in ret.keys():
            ret[key].load_state_dict(state_dict[key])
            ret[key].eval()
        return ret
    else:
        raise ValueError(f"Unknown model type: {model_type}")


def concat_feat(kp_source, kp_driving):
    if isinstance(kp_driving, torch.Tensor):
        feat = torch.cat([kp_source.view(kp_source.shape[0], -1), kp_driving.view(kp_driving.shape[0], -1)], dim=1)
    else:
        feat = torch.cat([kp_source.view(kp_source.shape[0], -1), kp_driving], dim=1)
    return feat


def calc_motion_multiplier(kp_source, kp_driving):
    dist = torch.norm(kp_driving - kp_source, dim=2).mean()
    return 1.0 / (dist + 1e-8)
