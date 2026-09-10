# Dreamtalk - Face Engine
# Extracted from Ditto
"""Ditto inference pipeline placeholder.

Full pipeline integrated into StreamSDK (stream_pipeline_offline.py).
This module re-exports the key pipeline components.
"""
from ditto_api import DittoAPI
from .config import DittoConfig

__all__ = ["DittoAPI", "DittoConfig"]
