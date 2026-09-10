# Dreamtalk - Face Engine
# Extracted from MuseTalk
#
# NOTE: Deliberately lazy. The full inference chain (musetalk_api -> inference ->
# utils.preprocessing) imports heavy optional deps (mmpose, face_detection) and
# even initializes a model at import time. We only import them on demand so that
# lightweight imports (e.g. `MuseTalkConfig`) work without those deps installed.

import importlib

__all__ = ["MuseTalkAPI", "MuseTalkInference", "MuseTalkConfig"]


def __getattr__(name):
    if name == "MuseTalkAPI":
        module = importlib.import_module(".musetalk_api", __name__)
        return module.MuseTalkAPI
    if name == "MuseTalkInference":
        module = importlib.import_module(".inference", __name__)
        return module.MuseTalkInference
    if name == "MuseTalkConfig":
        module = importlib.import_module(".config", __name__)
        return module.MuseTalkConfig
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
