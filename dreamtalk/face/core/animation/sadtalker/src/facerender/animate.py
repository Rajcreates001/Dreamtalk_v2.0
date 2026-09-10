# Dreamtalk - Face Engine
# Extracted from SadTalker
import os
import cv2
import numpy as np


class AnimateFromCoeff:
    def __init__(self, sadtalker_paths, device):
        self.paths = sadtalker_paths
        self.device = device

    def generate(self, data, save_dir, pic_path, crop_info, enhancer=None, background_enhancer=None, preprocess='crop', img_size=256):
        result_path = os.path.join(save_dir, 'result.mp4')
        return result_path
