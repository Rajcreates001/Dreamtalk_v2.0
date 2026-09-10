# Dreamtalk - Face Engine
# Extracted from LivePortrait
from torch import nn
import torch

from .convnextv2 import convnextv2_tiny
from .util import filter_state_dict

model_dict = {
    'convnextv2_tiny': convnextv2_tiny,
}


NUM_KP_DEFAULT = 21


class MotionExtractor(nn.Module):
    def __init__(self, **kwargs):
        super(MotionExtractor, self).__init__()
        backbone = kwargs.get('backbone', 'convnextv2_tiny')
        # Pass all kwargs (including num_kp) to backbone so ConvNeXtV2 gets num_kp
        self.detector = model_dict.get(backbone)(**kwargs)

    def forward(self, x):
        out = self.detector(x)
        return out
