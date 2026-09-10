# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: GPT_SoVITS/process_ckpt.py

import traceback
from collections import OrderedDict
from time import time as ttime
import shutil
import os
import torch
import hashlib
from io import BytesIO

model_version2byte = {
    "v3": b"03",
    "v4": b"04",
    "v2Pro": b"05",
    "v2ProPlus": b"06",
}

head2version = {
    b"00": ["v1", "v1", False],
    b"01": ["v2", "v2", False],
    b"02": ["v2", "v3", False],
    b"03": ["v2", "v3", True],
    b"04": ["v2", "v4", True],
    b"05": ["v2", "v2Pro", False],
    b"06": ["v2", "v2ProPlus", False],
}

hash_pretrained_dict = {
    "dc3c97e17592963677a4a1681f30c653": ["v2", "v2", False],
    "43797be674a37c1c83ee81081941ed0f": ["v2", "v3", False],
    "6642b37f3dbb1f76882b69937c95a5f3": ["v2", "v2", False],
    "4f26b9476d0c5033e04162c486074374": ["v2", "v4", False],
    "c7e9fce2223f3db685cdfa1e6368728a": ["v2", "v2Pro", False],
    "66b313e39455b57ab1b0bc0b239c9d0a": ["v2", "v2ProPlus", False],
}


def get_hash_from_file(sovits_path):
    with open(sovits_path, "rb") as f:
        data = f.read(8192)
    hash_md5 = hashlib.md5()
    hash_md5.update(data)
    return hash_md5.hexdigest()


def get_sovits_version_from_path_fast(sovits_path):
    h = get_hash_from_file(sovits_path)
    if h in hash_pretrained_dict:
        return hash_pretrained_dict[h]
    with open(sovits_path, "rb") as f:
        version = f.read(2)
    if version != b"PK":
        return head2version[version]
    if_lora_v3 = False
    size = os.path.getsize(sovits_path)
    if size < 82978 * 1024:
        model_version = version = "v1"
    elif size < 700 * 1024 * 1024:
        model_version = version = "v2"
    else:
        version = "v2"
        model_version = "v3"
    return version, model_version, if_lora_v3


def load_sovits_new(sovits_path):
    with open(sovits_path, "rb") as f:
        meta = f.read(2)
    if meta != b"PK":
        with open(sovits_path, "rb") as f:
            data = b"PK" + f.read()
        bio = BytesIO()
        bio.write(data)
        bio.seek(0)
        return torch.load(bio, map_location="cpu", weights_only=False)
    return torch.load(sovits_path, map_location="cpu", weights_only=False)
