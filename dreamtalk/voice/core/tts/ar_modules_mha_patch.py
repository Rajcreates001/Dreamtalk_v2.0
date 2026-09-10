# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: GPT_SoVITS/AR/modules/patched_mha_with_cache.py

import torch
from torch.nn.functional import pad, softmax, dropout
from torch import _softmax_backward_data as _softmax_backward_data_ref


def multi_head_attention_forward_patched(
    query, key, value, embed_dim_to_check, num_heads, in_proj_weight, in_proj_bias,
    bias_k, bias_v, add_zero_attn, dropout_p, out_proj_weight, out_proj_bias,
    training=True, key_padding_mask=None, need_weights=True, attn_mask=None,
    use_separate_proj_weight=False, q_proj_weight=None, k_proj_weight=None,
    v_proj_weight=None, static_k=None, static_v=None, average_attn_weights=True,
    cache=None,
):
    tgt_len, bsz, embed_dim = query.shape
    src_len = key.shape[0]
    assert embed_dim == embed_dim_to_check
    assert key.shape == value.shape

    head_dim = embed_dim // num_heads
    assert head_dim * num_heads == embed_dim

    if use_separate_proj_weight:
        q = q_proj_weight(query)
        k = k_proj_weight(key)
        v = v_proj_weight(value)
    else:
        qkv = torch.nn.functional.linear(query, in_proj_weight, in_proj_bias)
        q, k, v = qkv.chunk(3, dim=-1)

    q = q.contiguous().view(tgt_len, bsz * num_heads, head_dim).transpose(0, 1)
    k = k.contiguous().view(-1, bsz * num_heads, head_dim).transpose(0, 1)
    v = v.contiguous().view(-1, bsz * num_heads, head_dim).transpose(0, 1)

    if cache is not None:
        k = torch.cat([cache["k"], k], dim=1)
        v = torch.cat([cache["v"], v], dim=1)
        cache["k"] = k
        cache["v"] = v

    src_len = k.shape[1]

    if key_padding_mask is not None:
        assert key_padding_mask.shape[0] == bsz
        assert key_padding_mask.shape[1] == src_len

    if add_zero_attn:
        zero_attn_shape = (bsz * num_heads, 1, head_dim)
        k = torch.cat([k, torch.zeros(zero_attn_shape, dtype=k.dtype, device=k.device)], dim=1)
        v = torch.cat([v, torch.zeros(zero_attn_shape, dtype=v.dtype, device=v.device)], dim=1)
        if attn_mask is not None:
            attn_mask = pad(attn_mask, (0, 1))
        if key_padding_mask is not None:
            key_padding_mask = pad(key_padding_mask, (0, 1))

    attn_output = scaled_dot_product_attention(q, k, v, attn_mask, dropout_p, key_padding_mask)
    attn_output = attn_output.transpose(0, 1).contiguous().view(tgt_len * bsz, embed_dim)
    attn_output = torch.nn.functional.linear(attn_output, out_proj_weight, out_proj_bias)
    attn_output = attn_output.view(tgt_len, bsz, attn_output.size(1))
    return attn_output, None


def scaled_dot_product_attention(q, k, v, attn_mask=None, dropout_p=0.0, key_padding_mask=None):
    B, Nt, E = q.shape
    q = q / (E ** 0.5)
    attn = torch.bmm(q, k.transpose(-2, -1))
    if attn_mask is not None:
        attn += attn_mask
    if key_padding_mask is not None:
        attn = attn.view(B, -1, Nt, k.shape[1])
        attn = attn.masked_fill(key_padding_mask.unsqueeze(1).unsqueeze(2), float("-inf"))
        attn = attn.view(B, -1, k.shape[1])
    attn = softmax(attn, dim=-1)
    attn = dropout(attn, p=dropout_p, training=True)
    output = torch.bmm(attn, v)
    return output
