# Dreamtalk - Face Engine
# Extracted from LivePortrait
import os.path as osp
from dataclasses import dataclass


def make_abs_path(fn):
    return osp.join(osp.dirname(osp.realpath(__file__)), fn)


@dataclass
class PrintableConfig:
    def __repr__(self):
        lines = [self.__class__.__name__ + ':']
        for key, val in vars(self).items():
            if hasattr(val, 'shape'):
                val = val.shape
            lines += f'{key}: {val}'.split('\n')
        return '\n    '.join(lines)
