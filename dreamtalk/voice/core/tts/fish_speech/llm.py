# Dreamtalk - Voice Engine
# Extracted from Fish Speech (text2semantic LLM)

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from einops import rearrange
from torch import Tensor
from torch.nn.attention import SDPBackend, sdpa_kernel


def find_multiple(n: int, k: int) -> int:
    if n % k == 0:
        return n
    return n + k - (n % k)


def precompute_freqs_cis(seq_len: int, n_elem: int, base: int = 10000) -> Tensor:
    freqs = 1.0 / (base ** (torch.arange(0, n_elem, 2)[: (n_elem // 2)].float() / n_elem))
    t = torch.arange(seq_len, device=freqs.device)
    freqs = torch.outer(t, freqs)
    return torch.polar(torch.ones_like(freqs), freqs)


def apply_rotary_emb(x: Tensor, freqs_cis: Tensor) -> Tensor:
    x_ = torch.view_as_complex(x.float().reshape(*x.shape[:-1], -1, 2))
    freqs_cis = freqs_cis.unsqueeze(0).unsqueeze(2)
    x_out = torch.view_as_complex(x_.float() * freqs_cis).flatten(3)
    return x_out.type_as(x)


class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-5):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: Tensor) -> Tensor:
        x_dtype = x.dtype
        x = x.float()
        norm = torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return (x * norm).to(dtype=x_dtype) * self.weight


class KVCache(nn.Module):
    def __init__(self, max_batch_size, max_seq_len, n_heads, head_dim, dtype=torch.bfloat16):
        super().__init__()
        cache_shape = (max_batch_size, n_heads, max_seq_len, head_dim)
        self.register_buffer("k_cache", torch.zeros(cache_shape, dtype=dtype))
        self.register_buffer("v_cache", torch.zeros(cache_shape, dtype=dtype))

    def update(self, input_pos, k_val, v_val):
        assert input_pos.shape[0] == k_val.shape[2]
        k_out = self.k_cache
        v_out = self.v_cache
        k_out[:, :, input_pos] = k_val
        v_out[:, :, input_pos] = v_val
        return k_out, v_out


class Attention(nn.Module):
    def __init__(self, dim, n_head, n_local_heads, head_dim, dropout=0.0):
        super().__init__()
        self.n_head = n_head
        self.head_dim = head_dim
        self.n_local_heads = n_local_heads
        total_head_dim = (n_head + 2 * n_local_heads) * head_dim
        self.wqkv = nn.Linear(dim, total_head_dim, bias=False)
        self.wo = nn.Linear(head_dim * n_head, dim, bias=False)
        self.kv_cache = None
        self.attn_dropout = dropout

    def forward(self, x, freqs_cis, mask, input_pos=None):
        bsz, seqlen, _ = x.shape
        kv_size = self.n_local_heads * self.head_dim
        q, k, v = self.wqkv(x).split([kv_size, kv_size, kv_size], dim=-1)

        q = q.view(bsz, seqlen, self.n_head, self.head_dim)
        k = k.view(bsz, seqlen, self.n_local_heads, self.head_dim)
        v = v.view(bsz, seqlen, self.n_local_heads, self.head_dim)

        q = apply_rotary_emb(q, freqs_cis)
        k = apply_rotary_emb(k, freqs_cis)

        q, k, v = map(lambda x: x.transpose(1, 2), (q, k, v))

        if self.kv_cache is not None:
            k, v = self.kv_cache.update(input_pos, k, v)

        k = k.repeat_interleave(self.n_head // self.n_local_heads, dim=1)
        v = v.repeat_interleave(self.n_head // self.n_local_heads, dim=1)

        y = F.scaled_dot_product_attention(
            q, k, v,
            dropout_p=self.attn_dropout if self.training else 0.0,
            attn_mask=mask,
        )
        y = y.transpose(1, 2).contiguous().view(bsz, seqlen, -1)
        return self.wo(y)


class FeedForward(nn.Module):
    def __init__(self, dim, intermediate_size):
        super().__init__()
        self.w1 = nn.Linear(dim, intermediate_size, bias=False)
        self.w2 = nn.Linear(intermediate_size, dim, bias=False)
        self.w3 = nn.Linear(dim, intermediate_size, bias=False)

    def forward(self, x):
        return self.w2(F.silu(self.w1(x)) * self.w3(x))


class TransformerBlock(nn.Module):
    def __init__(self, dim, n_head, n_local_heads, head_dim, intermediate_size, dropout=0.0):
        super().__init__()
        self.attention = Attention(dim, n_head, n_local_heads, head_dim, dropout)
        self.feed_forward = FeedForward(dim, intermediate_size)
        self.attention_norm = RMSNorm(dim)
        self.ffn_norm = RMSNorm(dim)

    def forward(self, x, freqs_cis, mask, input_pos=None):
        h = x + self.attention(self.attention_norm(x), freqs_cis, mask, input_pos)
        out = h + self.feed_forward(self.ffn_norm(h))
        return out


@dataclass
class BaseModelArgs:
    model_type: str = "base"
    vocab_size: int = 32000
    n_layer: int = 32
    n_head: int = 32
    dim: int = 4096
    intermediate_size: int = None
    n_local_heads: int = -1
    head_dim: int = 64
    rope_base: float = 10000
    norm_eps: float = 1e-5
    max_seq_len: int = 2048
    dropout: float = 0.0
    tie_word_embeddings: bool = True
    codebook_size: int = 160
    num_codebooks: int = 4


@dataclass
class DualARModelArgs(BaseModelArgs):
    model_type: str = "dual_ar"
    n_fast_layer: int = 4
    fast_dim: int | None = None
    fast_n_head: int | None = None
    fast_n_local_heads: int | None = None
    fast_head_dim: int | None = None
    fast_intermediate_size: int | None = None
    norm_fastlayer_input: bool = False

    def __post_init__(self):
        super().__post_init__()
        self.fast_dim = self.fast_dim or self.dim
        self.fast_n_head = self.fast_n_head or self.n_head
        self.fast_n_local_heads = self.fast_n_local_heads or self.n_local_heads
        self.fast_head_dim = self.fast_head_dim or self.head_dim
        self.fast_intermediate_size = self.fast_intermediate_size or self.intermediate_size


@dataclass
class TransformerForwardResult:
    token_logits: Tensor
    codebook_logits: Tensor


class BaseTransformer(nn.Module):
    def __init__(self, config: BaseModelArgs) -> None:
        super().__init__()
        self.config = config
        self.embeddings = nn.Embedding(config.vocab_size, config.dim)
        self.codebook_embeddings = nn.Embedding(
            config.codebook_size * config.num_codebooks, config.dim,
        )
        self.layers = nn.ModuleList([
            TransformerBlock(
                config.dim, config.n_head, config.n_local_heads,
                config.head_dim, config.intermediate_size, config.dropout,
            )
            for _ in range(config.n_layer)
        ])
        self.norm = RMSNorm(config.dim, eps=config.norm_eps)
        self.output = nn.Linear(config.dim, config.vocab_size, bias=False) if not config.tie_word_embeddings else None

        self.register_buffer("freqs_cis", precompute_freqs_cis(
            config.max_seq_len, config.head_dim, config.rope_base,
        ), persistent=False)
        self.register_buffer("causal_mask", torch.tril(
            torch.ones(config.max_seq_len, config.max_seq_len, dtype=torch.bool),
        ), persistent=False)

        self.max_batch_size = -1
        self.max_seq_len = -1

    def setup_caches(self, max_batch_size, max_seq_len, dtype=torch.bfloat16):
        if self.max_seq_len >= max_seq_len and self.max_batch_size >= max_batch_size:
            return
        max_seq_len = find_multiple(max_seq_len, 8)
        self.max_seq_len = max_seq_len
        self.max_batch_size = max_batch_size
        for b in self.layers:
            b.attention.kv_cache = KVCache(max_batch_size, max_seq_len, b.attention.n_local_heads, b.attention.head_dim, dtype).to(self.norm.weight.device)

    def forward(self, tokens, input_pos=None, mask=None):
        if mask is None:
            mask = self.causal_mask[None, None, :tokens.shape[1], :tokens.shape[1]]
        freqs_cis = self.freqs_cis[input_pos] if input_pos is not None else self.freqs_cis[:tokens.shape[1]]
        h = self.embeddings(tokens)
        for layer in self.layers:
            h = layer(h, freqs_cis, mask, input_pos)
        h = self.norm(h)
        logits = self.output(h) if self.output is not None else h @ self.embeddings.weight.T
        return logits


class DualARTransformer(BaseTransformer):
    def __init__(self, config: DualARModelArgs) -> None:
        super().__init__(config)
        self.fast_embeddings = nn.Embedding(
            config.codebook_size * config.num_codebooks, config.fast_dim,
        )
        self.fast_layers = nn.ModuleList([
            TransformerBlock(
                config.fast_dim, config.fast_n_head, config.fast_n_local_heads,
                config.fast_head_dim, config.fast_intermediate_size,
            )
            for _ in range(config.n_fast_layer)
        ])
        self.fast_norm = RMSNorm(config.fast_dim, eps=config.norm_eps)
        self.fast_output = nn.Linear(config.fast_dim, config.codebook_size, bias=False)
        self.norm_fastlayer_input = config.norm_fastlayer_input

        self.register_buffer("fast_freqs_cis", precompute_freqs_cis(
            config.max_seq_len, config.fast_head_dim, config.rope_base,
        ), persistent=False)

    def forward_slow(self, tokens, input_pos=None, mask=None):
        if mask is None:
            mask = self.causal_mask[None, None, :tokens.shape[1], :tokens.shape[1]]
        freqs_cis = self.freqs_cis[input_pos] if input_pos is not None else self.freqs_cis[:tokens.shape[1]]
        h = self.embeddings(tokens)
        for layer in self.layers:
            h = layer(h, freqs_cis, mask, input_pos)
        h = self.norm(h)
        logits = self.output(h) if self.output is not None else h @ self.embeddings.weight.T
        return logits, h

    def forward_fast(self, hidden_states, codebook_tokens, input_pos=None):
        codebook_emb = self.fast_embeddings(codebook_tokens)
        codebook_emb = codebook_emb.sum(dim=-2)
        if self.norm_fastlayer_input:
            h = RMSNorm(self.config.fast_dim, eps=self.config.norm_eps).to(hidden_states.device)(hidden_states + codebook_emb)
        else:
            h = hidden_states + codebook_emb

        freqs_cis = self.fast_freqs_cis[input_pos] if input_pos is not None else self.fast_freqs_cis[:h.shape[1]]
        mask = self.causal_mask[None, None, :h.shape[1], :h.shape[1]]
        for layer in self.fast_layers:
            h = layer(h, freqs_cis, mask, input_pos)
        h = self.fast_norm(h)
        logits = self.fast_output(h)
        return logits

    def forward(self, tokens, input_pos=None, mask=None):
        slow_logits, hidden = self.forward_slow(tokens, input_pos, mask)
        batch_size, seq_len = tokens.shape
        # Use the last token's hidden state to predict codebook tokens
        last_hidden = hidden[:, -1:, :]
        codebook_logits = self.forward_fast(last_hidden, input_pos=input_pos)
        return TransformerForwardResult(token_logits=slow_logits, codebook_logits=codebook_logits)
