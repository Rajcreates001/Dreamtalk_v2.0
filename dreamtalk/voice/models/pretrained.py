# Dreamtalk - Voice Engine
# Pretrained model path management
# Extracted from GPT-SoVITS config.py

import os


PRETRAINED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pretrained")


class PretrainedPaths:
    cnhubert = os.path.join(PRETRAINED_DIR, "chinese-hubert-base")
    bert = os.path.join(PRETRAINED_DIR, "chinese-roberta-wwm-ext-large")

    sovits = {
        "v1": os.path.join(PRETRAINED_DIR, "s2G488k.pth"),
        "v2": os.path.join(PRETRAINED_DIR, "gsv-v2final-pretrained", "s2G2333k.pth"),
        "v3": os.path.join(PRETRAINED_DIR, "s2Gv3.pth"),
        "v4": os.path.join(PRETRAINED_DIR, "gsv-v4-pretrained", "s2Gv4.pth"),
    }

    gpt = {
        "v1": os.path.join(PRETRAINED_DIR, "s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt"),
        "v2": os.path.join(PRETRAINED_DIR, "gsv-v2final-pretrained", "s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt"),
        "v3": os.path.join(PRETRAINED_DIR, "s1v3.ckpt"),
        "v4": os.path.join(PRETRAINED_DIR, "s1v3.ckpt"),
    }
