# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: GPT_SoVITS/AR/models/t2s_model.py + t2s_lightning_module.py

import math
from typing import List, Optional

import torch
from torch import nn
from torch.nn import functional as F
from torchmetrics.classification import MulticlassAccuracy

from .ar_utils import dpo_loss, get_batch_logps, make_pad_mask, make_pad_mask_left, make_reject_y, sample, topk_sampling
from .ar_modules_embedding import SinePositionalEmbedding, TokenEmbedding
from .ar_modules_transformer import LayerNorm, TransformerEncoder, TransformerEncoderLayer

default_config = {
    "embedding_dim": 512,
    "hidden_dim": 512,
    "num_head": 8,
    "num_layers": 12,
    "num_codebook": 8,
    "p_dropout": 0.0,
    "vocab_size": 1024 + 1,
    "phoneme_vocab_size": 512,
    "EOS": 1024,
}


def scaled_dot_product_attention(query, key, value, attn_mask=None, scale=None):
    B, H, L, S = query.size(0), query.size(1), query.size(-2), key.size(-2)
    if scale is None:
        scale_factor = torch.tensor(1 / math.sqrt(query.size(-1)))
    else:
        scale_factor = scale
    attn_bias = torch.zeros(B, H, L, S, dtype=query.dtype, device=query.device)
    if attn_mask is not None:
        if attn_mask.dtype == torch.bool:
            attn_bias.masked_fill_(attn_mask, float("-inf"))
        else:
            attn_bias += attn_mask
    attn_weight = query @ key.transpose(-2, -1) * scale_factor
    attn_weight += attn_bias
    attn_weight = torch.softmax(attn_weight, dim=-1)
    if attn_mask is not None:
        if attn_mask.dtype == torch.bool:
            attn_weight.masked_fill_(attn_mask, 0)
        else:
            attn_mask[attn_mask != float("-inf")] = 0
            attn_mask[attn_mask == float("-inf")] = 1
            attn_weight.masked_fill_(attn_mask, 0)
    return attn_weight @ value


class T2SMLP:
    def __init__(self, w1, b1, w2, b2):
        self.w1 = w1
        self.b1 = b1
        self.w2 = w2
        self.b2 = b2

    def forward(self, x):
        x = F.relu(F.linear(x, self.w1, self.b1))
        x = F.linear(x, self.w2, self.b2)
        return x


class T2SBlock:
    def __init__(self, num_heads, hidden_dim: int, mlp: T2SMLP, qkv_w, qkv_b, out_w, out_b, norm_w1, norm_b1, norm_eps1, norm_w2, norm_b2, norm_eps2):
        self.num_heads = num_heads
        self.hidden_dim = hidden_dim
        self.mlp = mlp
        self.qkv_w = qkv_w
        self.qkv_b = qkv_b
        self.out_w = out_w
        self.out_b = out_b
        self.norm_w1 = norm_w1
        self.norm_b1 = norm_b1
        self.norm_eps1 = norm_eps1
        self.norm_w2 = norm_w2
        self.norm_b2 = norm_b2
        self.norm_eps2 = norm_eps2

    def forward(self, x, attn_mask, cache=None):
        if cache is not None and "ff" in cache:
            return self.forward_with_cache(x, attn_mask, cache)
        return self.forward_impl(x, attn_mask)

    def forward_impl(self, x, attn_mask):
        residual = x
        x = F.layer_norm(x, [self.hidden_dim], self.norm_w1, self.norm_b1, self.norm_eps1)
        qkv = F.linear(x, self.qkv_w, self.qkv_b)
        B, T, C = qkv.shape
        qkv = qkv.reshape(B, T, 3, self.num_heads, C // (3 * self.num_heads)).permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]
        attn = scaled_dot_product_attention(q, k, v, attn_mask)
        attn = attn.transpose(1, 2).reshape(B, T, C)
        x = F.linear(attn, self.out_w, self.out_b)
        x = residual + x
        residual = x
        x = F.layer_norm(x, [self.hidden_dim], self.norm_w2, self.norm_b2, self.norm_eps2)
        x = self.mlp.forward(x)
        x = residual + x
        return x

    def forward_with_cache(self, x, attn_mask, cache):
        k_cache = cache["k"]
        v_cache = cache["v"]
        residual = x
        x = F.layer_norm(x, [self.hidden_dim], self.norm_w1, self.norm_b1, self.norm_eps1)
        qkv = F.linear(x, self.qkv_w, self.qkv_b)
        B, T, C = qkv.shape
        qkv = qkv.reshape(B, T, 3, self.num_heads, C // (3 * self.num_heads)).permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]
        if k_cache is not None and v_cache is not None:
            k = torch.cat([k_cache, k], dim=-2)
            v = torch.cat([v_cache, v], dim=-2)
            cache["k"] = k
            cache["v"] = v
        attn = scaled_dot_product_attention(q, k, v)
        attn = attn.transpose(1, 2).reshape(B, T, C)
        x = F.linear(attn, self.out_w, self.out_b)
        x = residual + x
        residual = x
        x = F.layer_norm(x, [self.hidden_dim], self.norm_w2, self.norm_b2, self.norm_eps2)
        x = self.mlp.forward(x)
        x = residual + x
        return x


class Text2SemanticDecoder(nn.Module):
    def __init__(self, config, top_k=3):
        super(Text2SemanticDecoder, self).__init__()
        self.config = config
        self.top_k = top_k
        self.EOS = config.get("EOS", 1024)
        self.VOCAB_SIZE = config.get("vocab_size", 1024 + 1)
        self.phoneme_vocab_size = config.get("phoneme_vocab_size", 512)
        self.embedding_dim = config.get("embedding_dim", 512)
        self.hidden_dim = config.get("hidden_dim", 512)
        self.num_head = config.get("num_head", 8)
        self.num_layers = config.get("num_layers", 12)
        self.p_dropout = config.get("p_dropout", 0.0)
        self.num_codebook = config.get("num_codebook", 8)
        self.embedding = TokenEmbedding(self.embedding_dim, self.VOCAB_SIZE)
        self.ar_text_embedding = nn.Embedding(self.phoneme_vocab_size, self.embedding_dim)
        self.ar_text_position = SinePositionalEmbedding(self.embedding_dim, optional_trim=0)
        self.ar_audio_position = SinePositionalEmbedding(self.embedding_dim, optional_trim=0)
        self.ar_audio_embedding = nn.Embedding(self.VOCAB_SIZE, self.embedding_dim)
        self.bert_proj = nn.Linear(1024, self.embedding_dim)
        self.ar_text_embedding_bert = nn.Embedding(self.phoneme_vocab_size, self.embedding_dim)
        self.text_embedding_proj = nn.Linear(self.embedding_dim * 2, self.embedding_dim)
        self.text_embedding_proj2 = nn.Linear(self.embedding_dim * 2, self.embedding_dim)

        encoder_layer = TransformerEncoderLayer(
            d_model=self.embedding_dim,
            nhead=self.num_head,
            dim_feedforward=self.hidden_dim * 4,
            dropout=self.p_dropout,
            batch_first=True,
            activation="balanced_double_swish",
            norm_first=True,
        )
        self.encoder = TransformerEncoder(encoder_layer, self.num_layers)
        self.ar_audio_embedding_proj = nn.Linear(self.embedding_dim * 2, self.embedding_dim)
        self.predict_layer = nn.Linear(self.embedding_dim, self.VOCAB_SIZE)
        self.loss_fct = nn.CrossEntropyLoss(reduction="sum")
        self.accuracy_metric = MulticlassAccuracy(
            self.VOCAB_SIZE, top_k=self.top_k, average="micro", multidim_average="global"
        )

    def forward(self, phoneme_ids, phoneme_ids_len, semantic_ids, semantic_ids_len, bert_feature):
        return self.forward_old(phoneme_ids, phoneme_ids_len, semantic_ids, semantic_ids_len, bert_feature)

    def forward_old(self, phoneme_ids, phoneme_ids_len, semantic_ids, semantic_ids_len, bert_feature):
        bert_feature = bert_feature.permute(0, 2, 1)
        device = phoneme_ids.device
        max_len = torch.max(phoneme_ids_len).item()
        mask = make_pad_mask(phoneme_ids_len, max_len).to(device)

        text_embedding = self.ar_text_embedding(phoneme_ids)
        text_embedding = self.ar_text_position(text_embedding)
        bert_proj = self.bert_proj(bert_feature).permute(0, 2, 1)
        text_embedding = torch.cat([text_embedding, bert_proj], -1)
        text_embedding = self.text_embedding_proj(text_embedding)

        src = text_embedding
        x = self.encoder(src, src_key_padding_mask=mask)
        text_features = x

        audio_embedding = self.ar_audio_embedding(semantic_ids)
        audio_embedding = self.ar_audio_position(audio_embedding)
        audio_embedding = torch.cat([audio_embedding, text_features], -1)
        audio_embedding = self.ar_audio_embedding_proj(audio_embedding)
        text_embedding_bert = self.ar_text_embedding_bert(phoneme_ids)
        text_embedding_bert = torch.cat([text_embedding_bert, text_features], -1)
        text_embedding_bert = self.text_embedding_proj2(text_embedding_bert)

        src = torch.cat([text_embedding_bert, audio_embedding], dim=1)
        src_mask = make_pad_mask(phoneme_ids_len + semantic_ids_len, max_len * 2).to(device)
        x = self.encoder(src, src_key_padding_mask=src_mask)
        x = x[:, phoneme_ids.shape[1]:]

        logits = self.predict_layer(x)
        logits = logits[:, :-1, :].contiguous()
        targets = semantic_ids[:, 1:].contiguous()
        mask_labels = make_pad_mask_left(semantic_ids_len - 1, max_len - 1).to(device)
        loss = self.loss_fct(logits.view(-1, self.VOCAB_SIZE), targets.view(-1))
        acc = self.accuracy_metric(logits.view(-1, self.VOCAB_SIZE), targets.view(-1))
        return loss, acc

    def infer_panel_batch_infer(self, phoneme_ids, phoneme_ids_len, prompt, bert_feature, top_k, top_p, temperature, early_stop_num, max_len, repetition_penalty, **kwargs):
        return self.infer_panel_naive_batched(phoneme_ids, phoneme_ids_len, prompt, bert_feature, top_k, top_p, temperature, early_stop_num, max_len, repetition_penalty)

    def infer_panel_naive_batched(self, phoneme_ids, phoneme_ids_len, prompt, bert_feature, top_k, top_p, temperature, early_stop_num, max_len, repetition_penalty):
        device = phoneme_ids.device
        bert_feature = bert_feature.permute(0, 2, 1)
        max_phoneme_len = torch.max(phoneme_ids_len).item()
        mask = make_pad_mask(phoneme_ids_len, max_phoneme_len).to(device)

        text_embedding = self.ar_text_embedding(phoneme_ids)
        text_embedding = self.ar_text_position(text_embedding)
        bert_proj = self.bert_proj(bert_feature).permute(0, 2, 1)
        text_embedding = torch.cat([text_embedding, bert_proj], -1)
        text_embedding = self.text_embedding_proj(text_embedding)

        src = text_embedding
        x = self.encoder(src, src_key_padding_mask=mask)
        text_features = x

        text_embedding_bert = self.ar_text_embedding_bert(phoneme_ids)
        text_embedding_bert = torch.cat([text_embedding_bert, text_features], -1)
        text_embedding_bert = self.text_embedding_proj2(text_embedding_bert)

        if prompt is not None:
            prompt_audio_embedding = self.ar_audio_embedding(prompt)
            prompt_audio_embedding = self.ar_audio_position(prompt_audio_embedding)
            prompt_audio_embedding = torch.cat([prompt_audio_embedding, text_features], -1)
            prompt_audio_embedding = self.ar_audio_embedding_proj(prompt_audio_embedding)
            src = torch.cat([text_embedding_bert, prompt_audio_embedding], dim=1)
        else:
            src = text_embedding_bert

        src_mask = make_pad_mask(phoneme_ids_len, max_phoneme_len).to(device)
        if prompt is not None:
            prompt_len = prompt.shape[1]
            src_mask = make_pad_mask(phoneme_ids_len + prompt_len, max_phoneme_len + prompt_len).to(device)

        x = self.encoder(src, src_key_padding_mask=src_mask)
        x = x[:, phoneme_ids.shape[1]:]

        logits = self.predict_layer(x)
        logits = logits[:, :-1, :].contiguous()

        pred_semantic_list = []
        idx_list = []
        for b in range(logits.shape[0]):
            logit = logits[b:b+1]
            pred_semantic = torch.argmax(logit, dim=-1)
            idx = pred_semantic.shape[-1]
            pred_semantic_list.append(pred_semantic[0])
            idx_list.append(idx)

        return pred_semantic_list, idx_list

    def infer_panel_naive(self, phoneme_ids, phoneme_ids_len, prompt, bert_feature, top_k, top_p, temperature, early_stop_num, max_len, repetition_penalty, **kwargs):
        return self.infer(phoneme_ids, phoneme_ids_len, prompt, bert_feature, top_k, top_p, temperature, early_stop_num, max_len, repetition_penalty)

    @torch.no_grad()
    def infer(self, phoneme_ids, phoneme_ids_len, prompt, bert_feature, top_k, top_p, temperature, early_stop_num, max_len, repetition_penalty, **kwargs):
        device = next(self.parameters()).device
        bert_feature = bert_feature.permute(0, 2, 1)
        max_phoneme_len = torch.max(phoneme_ids_len).item()
        mask = make_pad_mask(phoneme_ids_len, max_phoneme_len).to(device)

        text_embedding = self.ar_text_embedding(phoneme_ids)
        text_embedding = self.ar_text_position(text_embedding)
        bert_proj = self.bert_proj(bert_feature).permute(0, 2, 1)
        text_embedding = torch.cat([text_embedding, bert_proj], -1)
        text_embedding = self.text_embedding_proj(text_embedding)

        x = self.encoder(text_embedding, src_key_padding_mask=mask)
        text_features = x

        text_embedding_bert = self.ar_text_embedding_bert(phoneme_ids)
        text_embedding_bert = torch.cat([text_embedding_bert, text_features], -1)
        text_embedding_bert = self.text_embedding_proj2(text_embedding_bert)

        if prompt is not None:
            prompt_audio_embedding = self.ar_audio_embedding(prompt)
            prompt_audio_embedding = self.ar_audio_position(prompt_audio_embedding)
            prompt_audio_embedding = torch.cat([prompt_audio_embedding, text_features], -1)
            prompt_audio_embedding = self.ar_audio_embedding_proj(prompt_audio_embedding)
            kv_src = torch.cat([text_embedding_bert, prompt_audio_embedding], dim=1)
            kv_mask = torch.cat([phoneme_ids, prompt], dim=1)
            prompt_len = prompt.shape[1]
        else:
            kv_src = text_embedding_bert
            kv_mask = phoneme_ids
            prompt_len = 0

        kv_src_mask = make_pad_mask(phoneme_ids_len, max_phoneme_len).to(device)
        if prompt is not None:
            kv_src_mask = make_pad_mask(phoneme_ids_len + prompt_len, max_phoneme_len + prompt_len).to(device)

        x = self.encoder(kv_src, src_key_padding_mask=kv_src_mask)
        x = x[:, phoneme_ids.shape[1]:]

        code_pred = []
        idx = 0
        while True:
            if idx == 0:
                logits = self.predict_layer(x[:, idx:idx+1])
            else:
                logits = self.predict_layer(x[:, idx:idx+1])

            logits = logits.squeeze(1)
            logits[0, self.EOS] *= repetition_penalty
            pred_token = sample(logits, top_k, top_p, temperature)
            code_pred.append(pred_token)
            idx += 1

            if pred_token[0, 0].item() == self.EOS:
                break
            if idx > early_stop_num:
                break

        pred_semantic = torch.cat(code_pred, dim=-1)
        return [pred_semantic[0]], [pred_semantic.shape[-1]]

    def infer_panel(self, phoneme_ids, phoneme_ids_len, prompt, bert_feature, top_k, top_p, temperature, early_stop_num, max_len, repetition_penalty, streaming_mode=False, chunk_length=16, mute_emb_sim_matrix=None, chunk_split_thershold=0.0, **kwargs):
        if streaming_mode:
            return self.infer_streaming(phoneme_ids, phoneme_ids_len, prompt, bert_feature, top_k, top_p, temperature, early_stop_num, max_len, repetition_penalty, chunk_length, mute_emb_sim_matrix, chunk_split_thershold)
        return self.infer(phoneme_ids, phoneme_ids_len, prompt, bert_feature, top_k, top_p, temperature, early_stop_num, max_len, repetition_penalty)

    def infer_streaming(self, phoneme_ids, phoneme_ids_len, prompt, bert_feature, top_k, top_p, temperature, early_stop_num, max_len, repetition_penalty, chunk_length, mute_emb_sim_matrix, chunk_split_thershold):
        device = next(self.parameters()).device
        bert_feature = bert_feature.permute(0, 2, 1)
        max_phoneme_len = torch.max(phoneme_ids_len).item()
        mask = make_pad_mask(phoneme_ids_len, max_phoneme_len).to(device)
        text_embedding = self.ar_text_embedding(phoneme_ids)
        text_embedding = self.ar_text_position(text_embedding)
        bert_proj = self.bert_proj(bert_feature).permute(0, 2, 1)
        text_embedding = torch.cat([text_embedding, bert_proj], -1)
        text_embedding = self.text_embedding_proj(text_embedding)
        x = self.encoder(text_embedding, src_key_padding_mask=mask)
        text_features = x
        text_embedding_bert = self.ar_text_embedding_bert(phoneme_ids)
        text_embedding_bert = torch.cat([text_embedding_bert, text_features], -1)
        text_embedding_bert = self.text_embedding_proj2(text_embedding_bert)
        if prompt is not None:
            prompt_audio_embedding = self.ar_audio_embedding(prompt)
            prompt_audio_embedding = self.ar_audio_position(prompt_audio_embedding)
            prompt_audio_embedding = torch.cat([prompt_audio_embedding, text_features], -1)
            prompt_audio_embedding = self.ar_audio_embedding_proj(prompt_audio_embedding)
            kv_src = torch.cat([text_embedding_bert, prompt_audio_embedding], dim=1)
            prompt_len = prompt.shape[1]
        else:
            kv_src = text_embedding_bert
            prompt_len = 0
        kv_src_mask = make_pad_mask(phoneme_ids_len + prompt_len, max_phoneme_len + prompt_len).to(device)
        x = self.encoder(kv_src, src_key_padding_mask=kv_src_mask)
        x = x[:, phoneme_ids.shape[1]:]
        idx = 0
        code_pred = []
        while True:
            if idx < x.shape[1]:
                logits = self.predict_layer(x[:, idx:idx+1])
            else:
                logits = self.predict_layer(x[:, -1:])
            logits = logits.squeeze(1)
            logits[0, self.EOS] *= repetition_penalty
            pred_token = sample(logits, top_k, top_p, temperature)
            code_pred.append(pred_token)
            idx += 1
            if idx % chunk_length == 0:
                chunk = torch.cat(code_pred[-chunk_length:], dim=-1)
                yield chunk, False
            if pred_token[0, 0].item() == self.EOS:
                break
            if idx > early_stop_num:
                break
        if len(code_pred) % chunk_length != 0:
            remaining = torch.cat(code_pred[-(len(code_pred) % chunk_length):], dim=-1)
            yield remaining, True
        else:
            yield None, True


class Text2SemanticLightningModule:
    def __init__(self, config, output_dir, is_train=True):
        self.config = config
        self.top_k = 3
        self.model = Text2SemanticDecoder(config=config, top_k=self.top_k)
        if not is_train:
            self.model.eval()
