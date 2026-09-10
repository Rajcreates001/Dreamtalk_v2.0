# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Copyright (c) 2024 NVIDIA CORPORATION.
# Source: GPT_SoVITS/BigVGAN/utils0.py

import torch


def init_weights(m, mean=0.0, std=0.01):
    classname = m.__class__.__name__
    if classname.find("Conv") != -1:
        m.weight.data.normal_(mean, std)


def get_padding(kernel_size, dilation=1):
    return int((kernel_size * dilation - dilation) / 2)
