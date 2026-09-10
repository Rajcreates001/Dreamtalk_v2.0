# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: GPT_SoVITS/config.py

import os
import re
import torch


pretrained_sovits_name = {
    "v1": "models/pretrained/s2G488k.pth",
    "v2": "models/pretrained/gsv-v2final-pretrained/s2G2333k.pth",
    "v3": "models/pretrained/s2Gv3.pth",
    "v4": "models/pretrained/gsv-v4-pretrained/s2Gv4.pth",
    "v2Pro": "models/pretrained/v2Pro/s2Gv2Pro.pth",
    "v2ProPlus": "models/pretrained/v2Pro/s2Gv2ProPlus.pth",
}

pretrained_gpt_name = {
    "v1": "models/pretrained/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt",
    "v2": "models/pretrained/gsv-v2final-pretrained/s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt",
    "v3": "models/pretrained/s1v3.ckpt",
    "v4": "models/pretrained/s1v3.ckpt",
    "v2Pro": "models/pretrained/s1v3.ckpt",
    "v2ProPlus": "models/pretrained/s1v3.ckpt",
}


class Config:
    def __init__(self):
        self.cnhubert_path = "models/pretrained/chinese-hubert-base"
        self.bert_path = "models/pretrained/chinese-roberta-wwm-ext-large"
        self.pretrained_sovits_path = pretrained_sovits_name.get("v2", "")
        self.pretrained_gpt_path = pretrained_gpt_name.get("v2", "")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.is_half = torch.cuda.is_available()
        self.exp_root = "logs"
        self.api_port = 9880
