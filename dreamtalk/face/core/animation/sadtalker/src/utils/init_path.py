# Dreamtalk - Face Engine
# Extracted from SadTalker
import os


def init_path(checkpoint_dir, config_dir, size=256, old_version=False, preprocess='crop'):
    paths = {
        'checkpoint_dir': checkpoint_dir,
        'config_dir': config_dir,
    }
    return paths
