# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: GPT_SoVITS/sv.py

import sys
import os
import torch


class SV:
    def __init__(self, device, is_half, model_path=None, eres2net_path=None):
        if model_path is None:
            model_path = os.environ.get(
                "SV_MODEL_PATH",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "pretrained_models", "sv", "pretrained_eres2netv2w24s4ep4.ckpt"),
            )
        if eres2net_path is not None:
            sys.path.append(eres2net_path)

        pretrained_state = torch.load(model_path, map_location="cpu", weights_only=False)
        from ERes2NetV2 import ERes2NetV2
        import kaldi as Kaldi

        embedding_model = ERes2NetV2(baseWidth=24, scale=4, expansion=4)
        embedding_model.load_state_dict(pretrained_state)
        embedding_model.eval()
        self.embedding_model = embedding_model
        if is_half:
            self.embedding_model = self.embedding_model.half().to(device)
        else:
            self.embedding_model = self.embedding_model.to(device)
        self.is_half = is_half
        self.kaldi = Kaldi

    def compute_embedding3(self, wav):
        with torch.no_grad():
            if self.is_half:
                wav = wav.half()
            feat = torch.stack([
                self.kaldi.fbank(wav0.unsqueeze(0), num_mel_bins=80, sample_frequency=16000, dither=0)
                for wav0 in wav
            ])
            sv_emb = self.embedding_model.forward3(feat)
        return sv_emb
