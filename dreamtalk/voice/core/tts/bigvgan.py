# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Copyright (c) 2024 NVIDIA CORPORATION.
# Source: GPT_SoVITS/BigVGAN/bigvgan.py

import os
import json
from pathlib import Path
from typing import Optional, Union, Dict

import torch
import torch.nn as nn
from torch.nn import Conv1d, ConvTranspose1d
from torch.nn.utils import weight_norm, remove_weight_norm

from .bigvgan_activations import Snake, SnakeBeta
from .bigvgan_utils import init_weights, get_padding
from .alias_free_activation.torch.act import Activation1d as TorchActivation1d
from .bigvgan_env import AttrDict

from huggingface_hub import PyTorchModelHubMixin, hf_hub_download


def load_hparams_from_json(path) -> AttrDict:
    with open(path) as f:
        data = f.read()
    return AttrDict(json.loads(data))


class AMPBlock1(torch.nn.Module):
    def __init__(self, h: AttrDict, channels: int, kernel_size: int = 3, dilation: tuple = (1, 3, 5), activation: str = None):
        super().__init__()
        self.h = h
        self.convs1 = nn.ModuleList([
            weight_norm(Conv1d(channels, channels, kernel_size, stride=1, dilation=d, padding=get_padding(kernel_size, d)))
            for d in dilation
        ])
        self.convs1.apply(init_weights)
        self.convs2 = nn.ModuleList([
            weight_norm(Conv1d(channels, channels, kernel_size, stride=1, dilation=1, padding=get_padding(kernel_size, 1)))
            for _ in range(len(dilation))
        ])
        self.convs2.apply(init_weights)
        self.num_layers = len(self.convs1) + len(self.convs2)

        if self.h.get("use_cuda_kernel", False):
            from .alias_free_activation.cuda.activation1d import Activation1d as CudaActivation1d
            Activation1d = CudaActivation1d
        else:
            Activation1d = TorchActivation1d

        act_class = Snake if activation == "snake" else (SnakeBeta if activation == "snakebeta" else None)
        if act_class is None:
            raise NotImplementedError(f"Unknown activation: {activation}")
        self.activations = nn.ModuleList([Activation1d(activation=act_class(channels)) for _ in range(self.num_layers)])

    def forward(self, x):
        acts1, acts2 = self.activations[::2], self.activations[1::2]
        for c1, c2, a1, a2 in zip(self.convs1, self.convs2, acts1, acts2):
            xt = a1(x)
            xt = c1(xt)
            xt = a2(xt)
            xt = c2(xt)
            x = xt + x
        return x

    def remove_weight_norm(self):
        for l in self.convs1:
            remove_weight_norm(l)
        for l in self.convs2:
            remove_weight_norm(l)


class AMPBlock2(torch.nn.Module):
    def __init__(self, h: AttrDict, channels: int, kernel_size: int = 3, dilation: tuple = (1, 3, 5), activation: str = None):
        super().__init__()
        self.h = h
        self.convs = nn.ModuleList([
            weight_norm(Conv1d(channels, channels, kernel_size, stride=1, dilation=d, padding=get_padding(kernel_size, d)))
            for d in dilation
        ])
        self.convs.apply(init_weights)
        self.num_layers = len(self.convs)

        if self.h.get("use_cuda_kernel", False):
            from .alias_free_activation.cuda.activation1d import Activation1d as CudaActivation1d
            Activation1d = CudaActivation1d
        else:
            Activation1d = TorchActivation1d

        act_class = Snake if activation == "snake" else (SnakeBeta if activation == "snakebeta" else None)
        if act_class is None:
            raise NotImplementedError(f"Unknown activation: {activation}")
        self.activations = nn.ModuleList([Activation1d(activation=act_class(channels)) for _ in range(self.num_layers)])

    def forward(self, x):
        for c, a in zip(self.convs, self.activations):
            xt = a(x)
            xt = c(xt)
            x = xt + x
        return x

    def remove_weight_norm(self):
        for l in self.convs:
            remove_weight_norm(l)


class BigVGAN(torch.nn.Module, PyTorchModelHubMixin):
    def __init__(self, h: AttrDict, use_cuda_kernel: bool = False):
        super().__init__()
        self.h = h
        self.h["use_cuda_kernel"] = use_cuda_kernel

        if self.h.get("use_cuda_kernel", False):
            from .alias_free_activation.cuda.activation1d import Activation1d as CudaActivation1d
            Activation1d = CudaActivation1d
        else:
            Activation1d = TorchActivation1d

        self.num_kernels = len(h.resblock_kernel_sizes)
        self.num_upsamples = len(h.upsample_rates)
        self.conv_pre = weight_norm(Conv1d(h.num_mels, h.upsample_initial_channel, 7, 1, padding=3))

        resblock_class = AMPBlock1 if h.resblock == "1" else (AMPBlock2 if h.resblock == "2" else None)
        if resblock_class is None:
            raise ValueError(f"Incorrect resblock class: {h.resblock}")

        self.ups = nn.ModuleList()
        for i, (u, k) in enumerate(zip(h.upsample_rates, h.upsample_kernel_sizes)):
            self.ups.append(nn.ModuleList([
                weight_norm(ConvTranspose1d(
                    h.upsample_initial_channel // (2 ** i),
                    h.upsample_initial_channel // (2 ** (i + 1)),
                    k, u, padding=(k - u) // 2,
                ))
            ]))

        self.resblocks = nn.ModuleList()
        for i in range(len(self.ups)):
            ch = h.upsample_initial_channel // (2 ** (i + 1))
            for j, (k, d) in enumerate(zip(h.resblock_kernel_sizes, h.resblock_dilation_sizes)):
                self.resblocks.append(resblock_class(h, ch, k, d, activation=h.activation))

        act_post_class = Snake if h.activation == "snake" else (SnakeBeta if h.activation == "snakebeta" else None)
        if act_post_class is None:
            raise NotImplementedError(f"Unknown activation: {h.activation}")
        self.activation_post = Activation1d(activation=act_post_class(h.upsample_initial_channel // (2 ** len(self.ups))))

        self.use_bias_at_final = h.get("use_bias_at_final", True)
        final_ch = h.upsample_initial_channel // (2 ** len(self.ups))
        self.conv_post = weight_norm(Conv1d(final_ch, 1, 7, 1, padding=3, bias=self.use_bias_at_final))

        for i in range(len(self.ups)):
            self.ups[i].apply(init_weights)
        self.conv_post.apply(init_weights)

        self.use_tanh_at_final = h.get("use_tanh_at_final", True)

    def forward(self, x):
        x = self.conv_pre(x)
        for i in range(self.num_upsamples):
            for i_up in range(len(self.ups[i])):
                x = self.ups[i][i_up](x)
            xs = None
            for j in range(self.num_kernels):
                if xs is None:
                    xs = self.resblocks[i * self.num_kernels + j](x)
                else:
                    xs += self.resblocks[i * self.num_kernels + j](x)
            x = xs / self.num_kernels
        x = self.activation_post(x)
        x = self.conv_post(x)
        if self.use_tanh_at_final:
            x = torch.tanh(x)
        else:
            x = torch.clamp(x, min=-1.0, max=1.0)
        return x

    def remove_weight_norm(self):
        try:
            for l in self.ups:
                for l_i in l:
                    remove_weight_norm(l_i)
            for l in self.resblocks:
                l.remove_weight_norm()
            remove_weight_norm(self.conv_pre)
            remove_weight_norm(self.conv_post)
        except ValueError:
            pass

    def _save_pretrained(self, save_directory: Path) -> None:
        model_path = save_directory / "bigvgan_generator.pt"
        torch.save({"generator": self.state_dict()}, model_path)
        config_path = save_directory / "config.json"
        with open(config_path, "w") as config_file:
            json.dump(self.h, config_file, indent=4)

    @classmethod
    def _from_pretrained(
        cls, *, model_id: str, revision: str, cache_dir: str, force_download: bool,
        proxies: Optional[Dict], resume_download: bool, local_files_only: bool,
        token: Union[str, bool, None], map_location: str = "cpu",
        strict: bool = False, use_cuda_kernel: bool = False, **model_kwargs,
    ):
        if os.path.isdir(model_id):
            config_file = os.path.join(model_id, "config.json")
        else:
            config_file = hf_hub_download(
                repo_id=model_id, filename="config.json", revision=revision,
                cache_dir=cache_dir, force_download=force_download,
                proxies=proxies, resume_download=resume_download,
                token=token, local_files_only=local_files_only,
            )
        h = load_hparams_from_json(config_file)
        model = cls(h, use_cuda_kernel=use_cuda_kernel)

        if os.path.isdir(model_id):
            model_file = os.path.join(model_id, "bigvgan_generator.pt")
        else:
            model_file = hf_hub_download(
                repo_id=model_id, filename="bigvgan_generator.pt", revision=revision,
                cache_dir=cache_dir, force_download=force_download,
                proxies=proxies, resume_download=resume_download,
                token=token, local_files_only=local_files_only,
            )
        checkpoint_dict = torch.load(model_file, map_location=map_location)
        try:
            model.load_state_dict(checkpoint_dict["generator"])
        except RuntimeError:
            model.remove_weight_norm()
            model.load_state_dict(checkpoint_dict["generator"])
        return model
