# Dreamtalk - Face Engine
# Extracted from SadTalker
import os
import cv2
import numpy as np


class CropAndExtract:
    def __init__(self, sadtalker_paths, device):
        self.paths = sadtalker_paths
        self.device = device

    def generate(self, pic_path, first_frame_dir, preprocess='crop', source_image_flag=True, pic_size=256):
        if not os.path.exists(pic_path):
            return None, None, None

        img = cv2.imread(pic_path)
        if img is None:
            return None, None, None

        # Save first frame
        first_frame_path = os.path.join(first_frame_dir, 'first_frame.png')
        cv2.imwrite(first_frame_path, img)

        # Create placeholder crop info
        crop_info = {
            'crop_pic_path': first_frame_path,
            'first_coeff_path': None,  # Set by external 3DMM extraction
        }

        return None, first_frame_path, crop_info
