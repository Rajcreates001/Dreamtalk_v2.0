# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Copyright (c) 2024 NVIDIA CORPORATION.
# Source: GPT_SoVITS/BigVGAN/env.py

from argparse import Namespace


class AttrDict(Namespace):
    def __init__(self, d):
        super().__init__(**{k: v for k, v in d.items() if isinstance(v, (int, float, str, bool, list, dict, tuple))})

    def __getattr__(self, attr):
        try:
            return super().__getattr__(attr)
        except AttributeError:
            return self.__dict__.get(attr, None)

    def get(self, key, default=None):
        try:
            return getattr(self, key)
        except AttributeError:
            return default
