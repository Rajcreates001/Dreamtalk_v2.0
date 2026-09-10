# Dreamtalk - Face Engine
# Extracted from SadTalker
import os
import torch
import uuid
import shutil

from .src.utils.preprocess import CropAndExtract
from .src.test_audio2coeff import Audio2Coeff
from .src.facerender.animate import AnimateFromCoeff
from .src.generate_batch import get_data
from .src.generate_facerender_batch import get_facerender_data
from .src.utils.init_path import init_path


class SadTalkerAPI:
    def __init__(self, checkpoint_path='checkpoints', config_path='src/config', device=None, lazy_load=False):
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.checkpoint_path = checkpoint_path
        self.config_path = config_path
        self.sadtalker_paths = None
        self.preprocess_model = None
        self.audio_to_coeff = None
        self.animate_from_coeff = None
        self._lazy_load = lazy_load

    def _init_models(self, size=256, preprocess='crop'):
        self.sadtalker_paths = init_path(
            self.checkpoint_path, self.config_path, size, False, preprocess
        )
        self.preprocess_model = CropAndExtract(self.sadtalker_paths, self.device)
        self.audio_to_coeff = Audio2Coeff(self.sadtalker_paths, self.device)
        self.animate_from_coeff = AnimateFromCoeff(self.sadtalker_paths, self.device)

    def generate(self, source_image, driven_audio, preprocess='crop',
                 still_mode=False, use_enhancer=False, batch_size=2, size=256,
                 pose_style=0, exp_scale=1.0, result_dir='./results',
                 ref_eyeblink=None, ref_pose=None,
                 input_yaw=None, input_pitch=None, input_roll=None):

        if not self._lazy_load or self.sadtalker_paths is None:
            self._init_models(size=size, preprocess=preprocess)

        time_tag = str(uuid.uuid4())
        save_dir = os.path.join(result_dir, time_tag)
        os.makedirs(save_dir, exist_ok=True)
        first_frame_dir = os.path.join(save_dir, 'first_frame_dir')
        os.makedirs(first_frame_dir, exist_ok=True)

        # Crop image and extract 3DMM
        first_coeff_path, crop_pic_path, crop_info = self.preprocess_model.generate(
            source_image, first_frame_dir, preprocess, source_image_flag=True, pic_size=size
        )
        if first_coeff_path is None:
            raise RuntimeError("No face detected in the source image")

        # Reference eye blink
        if ref_eyeblink is not None:
            ref_eyeblink_videoname = os.path.splitext(os.path.split(ref_eyeblink)[-1])[0]
            ref_eyeblink_frame_dir = os.path.join(save_dir, ref_eyeblink_videoname)
            os.makedirs(ref_eyeblink_frame_dir, exist_ok=True)
            ref_eyeblink_coeff_path, _, _ = self.preprocess_model.generate(
                ref_eyeblink, ref_eyeblink_frame_dir, preprocess, source_image_flag=False
            )
        else:
            ref_eyeblink_coeff_path = None

        if ref_pose is not None:
            if ref_pose == ref_eyeblink:
                ref_pose_coeff_path = ref_eyeblink_coeff_path
            else:
                ref_pose_videoname = os.path.splitext(os.path.split(ref_pose)[-1])[0]
                ref_pose_frame_dir = os.path.join(save_dir, ref_pose_videoname)
                os.makedirs(ref_pose_frame_dir, exist_ok=True)
                ref_pose_coeff_path, _, _ = self.preprocess_model.generate(
                    ref_pose, ref_pose_frame_dir, preprocess, source_image_flag=False
                )
        else:
            ref_pose_coeff_path = None

        # Audio to coeff
        batch = get_data(first_coeff_path, driven_audio, self.device,
                         ref_eyeblink_coeff_path=ref_eyeblink_coeff_path, still=still_mode)
        coeff_path = self.audio_to_coeff.generate(batch, save_dir, pose_style, ref_pose_coeff_path)

        # Coeff to video
        data = get_facerender_data(
            coeff_path, crop_pic_path, first_coeff_path, driven_audio,
            batch_size, input_yaw, input_pitch, input_roll,
            expression_scale=exp_scale, still_mode=still_mode,
            preprocess=preprocess, size=size
        )
        result = self.animate_from_coeff.generate(
            data, save_dir, source_image, crop_info,
            enhancer='gfpgan' if use_enhancer else None,
            preprocess=preprocess, img_size=size
        )

        return result
