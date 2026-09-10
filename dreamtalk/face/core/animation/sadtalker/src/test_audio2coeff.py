# Dreamtalk - Face Engine
# Extracted from SadTalker
import os
import torch
import numpy as np


class Audio2Coeff:
    def __init__(self, sadtalker_paths, device):
        self.paths = sadtalker_paths
        self.device = device
        self.net = None
        self._init_network()

    def _init_network(self):
        pass

    def generate(self, batch, save_dir, pose_style=0, ref_pose_coeff_path=None):
        coeff_path = os.path.join(save_dir, 'coeff_3dmm.mat')
        return coeff_path
