# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: GPT_SoVITS/module/attentions.py

import math
import torch
from torch import nn
from torch.nn import functional as F
from . import commons
from .modules import LayerNorm


class Encoder(nn.Module):
    def __init__(self, hidden_channels, filter_channels, n_heads, n_layers, kernel_size=1, p_dropout=0.0, window_size=4, isflow=False, **kwargs):
        super().__init__()
        self.hidden_channels = hidden_channels
        self.filter_channels = filter_channels
        self.n_heads = n_heads
        self.n_layers = n_layers
        self.kernel_size = kernel_size
        self.p_dropout = p_dropout
        self.window_size = window_size
        self.drop = nn.Dropout(p_dropout)
        self.attn_layers = nn.ModuleList()
        self.norm_layers_1 = nn.ModuleList()
        self.ffn_layers = nn.ModuleList()
        self.norm_layers_2 = nn.ModuleList()
        for i in range(self.n_layers):
            self.attn_layers.append(MultiHeadAttention(hidden_channels, hidden_channels, n_heads, p_dropout=p_dropout, window_size=window_size))
            self.norm_layers_1.append(LayerNorm(hidden_channels))
            self.ffn_layers.append(FFN(hidden_channels, hidden_channels, filter_channels, kernel_size, p_dropout=p_dropout))
            self.norm_layers_2.append(LayerNorm(hidden_channels))
        if isflow:
            cond_layer = torch.nn.Conv1d(kwargs["gin_channels"], 2 * hidden_channels * n_layers, 1)
            self.cond_pre = torch.nn.Conv1d(hidden_channels, 2 * hidden_channels, 1)
            self.cond_layer = weight_norm_modules(cond_layer, name="weight")
            self.gin_channels = kwargs["gin_channels"]

    def forward(self, x, x_mask, g=None):
        attn_mask = x_mask.unsqueeze(2) * x_mask.unsqueeze(-1)
        x = x * x_mask
        if g is not None:
            g = self.cond_layer(g)
        for i in range(self.n_layers):
            if g is not None:
                x = self.cond_pre(x)
                cond_offset = i * 2 * self.hidden_channels
                g_l = g[:, cond_offset : cond_offset + 2 * self.hidden_channels, :]
                x = commons.fused_add_tanh_sigmoid_multiply(x, g_l, torch.IntTensor([self.hidden_channels]))
            y = self.attn_layers[i](x, x, attn_mask)
            y = self.drop(y)
            x = self.norm_layers_1[i](x + y)
            y = self.ffn_layers[i](x, x_mask)
            y = self.drop(y)
            x = self.norm_layers_2[i](x + y)
        x = x * x_mask
        return x


class Decoder(nn.Module):
    def __init__(self, hidden_channels, filter_channels, n_heads, n_layers, kernel_size=1, p_dropout=0.0, proximal_bias=False, proximal_init=True, **kwargs):
        super().__init__()
        self.hidden_channels = hidden_channels
        self.filter_channels = filter_channels
        self.n_heads = n_heads
        self.n_layers = n_layers
        self.kernel_size = kernel_size
        self.p_dropout = p_dropout
        self.proximal_bias = proximal_bias
        self.proximal_init = proximal_init
        self.drop = nn.Dropout(p_dropout)
        self.self_attn_layers = nn.ModuleList()
        self.norm_layers_0 = nn.ModuleList()
        self.encdec_attn_layers = nn.ModuleList()
        self.norm_layers_1 = nn.ModuleList()
        self.ffn_layers = nn.ModuleList()
        self.norm_layers_2 = nn.ModuleList()
        for i in range(self.n_layers):
            self.self_attn_layers.append(MultiHeadAttention(hidden_channels, hidden_channels, n_heads, p_dropout=p_dropout, proximal_bias=proximal_bias, proximal_init=proximal_init))
            self.norm_layers_0.append(LayerNorm(hidden_channels))
            self.encdec_attn_layers.append(MultiHeadAttention(hidden_channels, hidden_channels, n_heads, p_dropout=p_dropout))
            self.norm_layers_1.append(LayerNorm(hidden_channels))
            self.ffn_layers.append(FFN(hidden_channels, hidden_channels, filter_channels, kernel_size, p_dropout=p_dropout))
            self.norm_layers_2.append(LayerNorm(hidden_channels))

    def forward(self, x, y, x_mask, y_mask):
        attn_mask = x_mask.unsqueeze(2) * x_mask.unsqueeze(-1)
        y_attn_mask = y_mask.unsqueeze(2) * y_mask.unsqueeze(-1)
        x = x * x_mask
        y = y * y_mask
        for i in range(self.n_layers):
            y = self.norm_layers_0[i](y + self.self_attn_layers[i](y, y, y_attn_mask))
            y = self.norm_layers_1[i](y + self.encdec_attn_layers[i](y, x, attn_mask))
            y = self.norm_layers_2[i](y + self.ffn_layers[i](y, y_mask))
        y = y * y_mask
        return y


class MultiHeadAttention(nn.Module):
    def __init__(self, channels, out_channels, n_heads, p_dropout=0.0, window_size=None, heads_share=True, block_length=None, proximal_bias=False, proximal_init=False):
        super().__init__()
        assert channels % n_heads == 0
        self.channels = channels
        self.out_channels = out_channels
        self.n_heads = n_heads
        self.p_dropout = p_dropout
        self.window_size = window_size
        self.heads_share = heads_share
        self.block_length = block_length
        self.proximal_bias = proximal_bias
        self.proximal_init = proximal_init
        self.attn = None
        self.k_channels = channels // n_heads
        self.conv_q = nn.Conv1d(channels, channels, 1)
        self.conv_k = nn.Conv1d(channels, channels, 1)
        self.conv_v = nn.Conv1d(channels, channels, 1)
        self.conv_o = nn.Conv1d(channels, out_channels, 1)
        self.drop = nn.Dropout(p_dropout)
        if window_size is not None:
            n_heads_rel = 1 if heads_share else n_heads
            self.relative_positions = self._get_relative_positions(window_size)
            self.head_weights = nn.Parameter(torch.zeros((n_heads_rel, window_size)))
            self.l_hop = nn.Parameter(torch.randn(window_size))
        if proximal_init:
            nn.init.constant_(self.conv_q.weight, 0)
            nn.init.constant_(self.conv_k.weight, 0)

    def forward(self, x, c, attn_mask=None):
        q = self.conv_q(x)
        k = self.conv_k(c)
        v = self.conv_v(c)
        x, self.attn = self.attention(q, k, v, mask=attn_mask)
        x = self.conv_o(x)
        return x

    def attention(self, query, key, value, mask=None):
        b, d, t_s, t_t = (*key.shape, query.shape[2])
        query = query.view(b, self.n_heads, self.k_channels, t_t).transpose(2, 3)
        key = key.view(b, self.n_heads, self.k_channels, t_s).transpose(2, 3)
        value = value.view(b, self.n_heads, self.k_channels, t_s).transpose(2, 3)
        scores = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(self.k_channels)
        if self.window_size is not None:
            assert t_s == t_t
            scores = self._apply_relative_scores(scores)
        if self.proximal_bias:
            assert t_s == t_t
            scores = self._apply_proximal_bias(scores, t_s)
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e4)
        p_attn = F.softmax(scores, dim=-1)
        p_attn = self.drop(p_attn)
        output = torch.matmul(p_attn, value)
        output = output.transpose(2, 3).contiguous().view(b, d, t_t)
        return output, p_attn

    def _apply_relative_scores(self, scores):
        b, h, t, t2 = scores.shape
        assert t == t2
        rel_pos = self.relative_positions[:t, :t].unsqueeze(0).unsqueeze(0)
        rel_pos = rel_pos.to(scores.device)
        if self.heads_share:
            head_weights = self.head_weights.view(1, 1, -1, 1)
        else:
            head_weights = self.head_weights.view(1, h, -1, 1)
        l_hop = self.l_hop[:t].view(1, 1, 1, -1)
        scores = scores + rel_pos * head_weights * l_hop
        return scores

    def _get_relative_positions(self, window_size):
        arange = torch.arange(window_size)
        relative_positions = arange[None, :] - arange[:, None]
        return relative_positions

    def _apply_proximal_bias(self, scores, length):
        r = torch.arange(length, device=scores.device)
        diff = r[None, :] - r[:, None]
        mask = (diff < -2) | (diff > 0)
        scores = scores.masked_fill(mask.unsqueeze(0).unsqueeze(0), -1e4)
        return scores


class FFN(nn.Module):
    def __init__(self, in_channels, out_channels, filter_channels, kernel_size, p_dropout=0.0, activation=None, causal=False):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.filter_channels = filter_channels
        self.kernel_size = kernel_size
        self.p_dropout = p_dropout
        self.activation = activation
        self.causal = causal
        self.conv_1 = nn.Conv1d(in_channels, filter_channels, kernel_size, padding=kernel_size // 2)
        self.conv_2 = nn.Conv1d(filter_channels, out_channels, kernel_size, padding=kernel_size // 2)
        self.drop = nn.Dropout(p_dropout)

    def forward(self, x, x_mask):
        x = self.conv_1(x * x_mask)
        if self.activation == "gelu":
            x = F.gelu(x)
        elif self.activation == "tanh":
            x = torch.tanh(x)
        else:
            x = F.relu(x)
        x = self.drop(x)
        x = self.conv_2(x * x_mask)
        return x * x_mask


from torch.nn.utils import weight_norm as weight_norm_modules
