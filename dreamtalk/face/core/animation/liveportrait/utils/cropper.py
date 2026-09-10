# Dreamtalk - Face Engine
# Extracted from LivePortrait
import cv2
import numpy as np
import os.path as osp

from .crop import prepare_paste_back
from .io import load_image_rgb
from .helper import is_video


class Cropper:
    def __init__(self, crop_cfg):
        self.crop_cfg = crop_cfg

    def crop_source_image(self, img_rgb, crop_cfg):
        """Crop face from source image. Returns crop info dict."""
        # Placeholder - actual implementation uses insightface/FaceAnalysis
        h, w = img_rgb.shape[:2]
        # For now, return a minimal crop info
        M_c2o = np.eye(2, 3, dtype=np.float32)
        crop_info = {
            'img_crop_256x256': cv2.resize(img_rgb, (256, 256)),
            'lmk_crop': None,
            'M_c2o': M_c2o,
        }
        return crop_info

    def crop_source_video(self, rgb_lst, crop_cfg):
        """Crop faces from source video frames."""
        frame_crop_lst = []
        lmk_crop_lst = []
        M_c2o_lst = []
        for img in rgb_lst:
            crop_info = self.crop_source_image(img, crop_cfg)
            frame_crop_lst.append(crop_info['img_crop_256x256'])
            lmk_crop_lst.append(crop_info['lmk_crop'])
            M_c2o_lst.append(crop_info['M_c2o'])
        return {'frame_crop_lst': frame_crop_lst, 'lmk_crop_lst': lmk_crop_lst, 'M_c2o_lst': M_c2o_lst}

    def crop_driving_video(self, rgb_lst):
        """Crop faces from driving video frames."""
        frame_crop_lst = []
        lmk_crop_lst = []
        for img in rgb_lst:
            crop_info = self.crop_source_image(img, self.crop_cfg)
            frame_crop_lst.append(crop_info['img_crop_256x256'])
            lmk_crop_lst.append(crop_info['lmk_crop'])
        return {'frame_crop_lst': frame_crop_lst, 'lmk_crop_lst': lmk_crop_lst}

    def calc_lmk_from_cropped_image(self, img_rgb):
        """Calculate landmarks from a cropped image."""
        return None

    def calc_lmks_from_cropped_video(self, rgb_lst):
        """Calculate landmarks from cropped video frames."""
        return [None] * len(rgb_lst)
