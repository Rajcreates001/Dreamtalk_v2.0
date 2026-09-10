# Dreamtalk - Voice Engine
# Extracted from ChatTTS

import os
import logging
from typing import Union, IO
from dataclasses import is_dataclass

import torch
from safetensors import safe_open


if hasattr(torch.serialization, "FILE_LIKE"):
    FileLike = torch.serialization.FILE_LIKE
elif hasattr(torch.types, "FILE_LIKE"):
    FileLike = torch.types.FileLike
else:
    FileLike = Union[str, os.PathLike, IO[bytes]]


@torch.inference_mode()
def load_safetensors(filename: str):
    state_dict_tensors = {}
    with safe_open(filename, framework="pt") as f:
        for k in f.keys():
            state_dict_tensors[k] = f.get_tensor(k)
    return state_dict_tensors


def del_all(d: Union[dict, list]):
    if is_dataclass(d):
        for k in list(vars(d).keys()):
            x = getattr(d, k)
            if isinstance(x, dict) or isinstance(x, list) or is_dataclass(x):
                del_all(x)
            del x
            delattr(d, k)
    elif isinstance(d, dict):
        lst = list(d.keys())
        for k in lst:
            x = d.pop(k)
            if isinstance(x, dict) or isinstance(x, list) or is_dataclass(x):
                del_all(x)
            del x
    elif isinstance(d, list):
        while len(d):
            x = d.pop()
            if isinstance(x, dict) or isinstance(x, list) or is_dataclass(x):
                del_all(x)
            del x
    else:
        del d


def select_device(min_memory=2047, experimental=False):
    has_cuda = torch.cuda.is_available()
    if has_cuda:
        dev_idx = 0
        max_free_memory = -1
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            free_memory = props.total_memory - torch.cuda.memory_reserved(i)
            if max_free_memory < free_memory:
                dev_idx = i
                max_free_memory = free_memory
        free_memory_mb = max_free_memory / (1024 * 1024)
        if free_memory_mb < min_memory:
            device = torch.device("cpu")
        else:
            device = torch.device(f"cuda:{dev_idx}")
    elif torch.backends.mps.is_available() and experimental:
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    return device
