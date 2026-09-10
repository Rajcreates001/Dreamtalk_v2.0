# Dreamtalk - Voice Engine
# Extracted from Fish Speech (sampling and inference logic)

from typing import Optional, Tuple

import torch
import torch.nn.functional as F

from .llm import BaseTransformer, DualARTransformer, TransformerForwardResult


def multinomial_sample_one_no_sync(probs_sort):
    q = torch.rand_like(probs_sort)
    q = -torch.log(q)
    return torch.argmax(probs_sort / q, dim=-1, keepdim=True).to(dtype=torch.int)


def logits_to_probs(logits, temperature, top_p, top_k):
    sorted_logits, sorted_indices = torch.sort(logits, descending=True)
    cum_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)

    indices = torch.arange(sorted_logits.shape[-1], device=sorted_logits.device)
    top_k_mask = indices >= top_k
    sorted_indices_to_remove = (cum_probs > top_p) | top_k_mask
    sorted_indices_to_remove[0] = False

    indices_to_remove = sorted_indices_to_remove.scatter(
        dim=-1, index=sorted_indices, src=sorted_indices_to_remove
    )
    logits = torch.where(indices_to_remove, float("-Inf"), logits)
    logits = logits / torch.clip(temperature, min=1e-5)
    probs = F.softmax(logits, dim=-1)
    return probs


def sample(logits, temperature, top_p, top_k):
    probs = logits_to_probs(logits, temperature, top_p, top_k)
    idx_next = multinomial_sample_one_no_sync(probs)
    return idx_next


@torch.inference_mode()
def generate_text_tokens(
    model: BaseTransformer,
    input_ids: torch.Tensor,
    max_new_tokens: int = 2048,
    temperature: float = 0.7,
    top_p: float = 0.9,
    top_k: int = 50,
    eos_token_id: int = 2,
    repeat_penalty: float = 1.0,
    max_seq_len: int = 2048,
) -> torch.Tensor:
    model.eval()
    device = next(model.parameters()).device
    input_ids = input_ids.to(device)
    seq_len = input_ids.shape[1]

    model.setup_caches(max_batch_size=1, max_seq_len=max_seq_len)

    for i in range(max_new_tokens):
        input_pos = torch.arange(seq_len + i, device=device)

        if seq_len + i > max_seq_len:
            logits = model(input_ids[:, -(max_seq_len):], input_pos=input_pos[-(max_seq_len):])
        else:
            logits = model(input_ids, input_pos=input_pos)

        next_logits = logits[:, -1, :]

        if repeat_penalty != 1.0:
            for token_id in set(input_ids[0].tolist()):
                if next_logits[0, token_id] < 0:
                    next_logits[0, token_id] *= repeat_penalty
                else:
                    next_logits[0, token_id] /= repeat_penalty

        next_token = sample(next_logits, temperature, top_p, top_k)

        if next_token.item() == eos_token_id:
            break

        input_ids = torch.cat([input_ids, next_token], dim=-1)

    model.max_batch_size = -1
    model.max_seq_len = -1
    for b in model.layers:
        b.attention.kv_cache = None

    return input_ids


@torch.inference_mode()
def generate_with_codes(
    model: DualARTransformer,
    input_ids: torch.Tensor,
    max_new_tokens: int = 2048,
    temperature_text: float = 0.7,
    top_p_text: float = 0.9,
    top_k_text: int = 50,
    temperature_codes: float = 0.3,
    top_p_codes: float = 0.9,
    top_k_codes: int = 50,
    eos_token_id: int = 2,
    max_seq_len: int = 2048,
) -> Tuple[torch.Tensor, torch.Tensor]:
    model.eval()
    device = next(model.parameters()).device
    input_ids = input_ids.to(device)
    num_codebooks = model.config.num_codebooks
    codebook_size = model.config.codebook_size

    model.setup_caches(max_batch_size=1, max_seq_len=max_seq_len)

    generated_tokens = input_ids.clone()
    all_codes = []

    for i in range(max_new_tokens):
        current_len = generated_tokens.shape[1]
        input_pos = torch.arange(current_len, device=device)

        if current_len > max_seq_len:
            slice_tokens = generated_tokens[:, -(max_seq_len):]
            slice_pos = input_pos[-(max_seq_len):]
            slow_result = model.forward_slow(slice_tokens, input_pos=slice_pos)
        else:
            slow_result = model.forward_slow(generated_tokens, input_pos=input_pos)

        next_logits = slow_result[0][:, -1, :]
        next_token = sample(next_logits, temperature_text, top_p_text, top_k_text)

        if next_token.item() == eos_token_id:
            break

        generated_tokens = torch.cat([generated_tokens, next_token], dim=-1)

        # Generate codebook tokens from hidden state
        last_hidden = slow_result[1][:, -1:, :]
        code_logits = model.forward_fast(last_hidden, input_pos=torch.tensor([current_len], device=device))
        codes = []
        for cb_idx in range(num_codebooks):
            cb_logits = code_logits[:, :, cb_idx * codebook_size:(cb_idx + 1) * codebook_size]
            cb_token = sample(cb_logits, temperature_codes, top_p_codes, top_k_codes)
            codes.append(cb_token)

        codes = torch.stack(codes, dim=-1)
        all_codes.append(codes)

    model.max_batch_size = -1
    model.max_seq_len = -1
    for b in model.layers:
        b.attention.kv_cache = None

    codes = torch.cat(all_codes, dim=1) if all_codes else torch.zeros(1, 0, num_codebooks, device=device)
    return generated_tokens, codes
