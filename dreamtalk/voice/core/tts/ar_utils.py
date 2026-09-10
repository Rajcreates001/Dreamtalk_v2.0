# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: GPT_SoVITS/AR/models/utils.py

import torch
import torch.nn.functional as F
from typing import List, Optional


def make_pad_mask(lengths: torch.Tensor, max_len: int = None) -> torch.Tensor:
    batch_size = lengths.size(0)
    if max_len is None:
        max_len = torch.max(lengths).item()
    ids = torch.arange(0, max_len, device=lengths.device).unsqueeze(0).expand(batch_size, -1)
    mask = ids >= lengths.unsqueeze(1).expand(-1, max_len)
    return mask


def make_pad_mask_left(lengths: torch.Tensor, max_len: int = None) -> torch.Tensor:
    batch_size = lengths.size(0)
    if max_len is None:
        max_len = torch.max(lengths).item()
    ids = torch.arange(0, max_len, device=lengths.device).unsqueeze(0).expand(batch_size, -1)
    mask = ids < (max_len - lengths.unsqueeze(1).expand(-1, max_len))
    return mask


def make_reject_y(y: torch.Tensor, y_lengths: torch.Tensor) -> torch.Tensor:
    reject_y = torch.zeros_like(y)
    for i in range(y.size(0)):
        reject_y[i, :y_lengths[i]] = y[i, :y_lengths[i]].flip(0)
    return reject_y


def topk_sampling(logits: torch.Tensor, top_k: int, top_p: float, temperature: float = 1.0):
    if temperature != 1.0:
        logits = logits / temperature
    if top_k > 0:
        indices_to_remove = torch.topk(logits, top_k)[0][..., -1, None]
        logits[logits < indices_to_remove] = float("-inf")
    if top_p > 0.0:
        sorted_logits, sorted_indices = torch.sort(logits, descending=True)
        cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
        sorted_indices_to_remove = cumulative_probs > top_p
        sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
        sorted_indices_to_remove[..., 0] = 0
        indices_to_remove = sorted_indices_to_remove.scatter(-1, sorted_indices, sorted_indices_to_remove)
        logits[indices_to_remove] = float("-inf")
    return logits


def sample(logits: torch.Tensor, top_k: int, top_p: float, temperature: float = 1.0):
    logits = topk_sampling(logits, top_k, top_p, temperature)
    probs = F.softmax(logits, dim=-1)
    return torch.multinomial(probs, num_samples=1)


def dpo_loss(policy_chosen_logps, policy_rejected_logps, reference_chosen_logps, reference_rejected_logps, beta):
    pi_ratio = policy_chosen_logps - policy_rejected_logps
    ref_ratio = reference_chosen_logps - reference_rejected_logps
    logits = pi_ratio - ref_ratio
    losses = -F.logsigmoid(beta * logits)
    return losses


def get_batch_logps(logits, labels, label_mask):
    per_token_logps = logits.gather(-1, labels.unsqueeze(-1)).squeeze(-1)
    return (per_token_logps * label_mask).sum(-1)
