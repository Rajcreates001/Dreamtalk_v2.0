# Dreamtalk - Voice Engine
# Extracted from ChatTTS

import logging
from dataclasses import dataclass
from typing import Union, List, Optional, Tuple, Callable

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.nn.utils.parametrize as P
from tqdm import tqdm
from transformers import LlamaModel, LlamaConfig
from transformers.cache_utils import Cache
from transformers.modeling_outputs import BaseModelOutputWithPast

from .utils import del_all
from .embed import Embed


class GPT(nn.Module):
    def __init__(
        self,
        gpt_config: dict,
        embed: Embed,
        use_flash_attn=False,
        use_vllm=False,
        device=torch.device("cpu"),
        device_gpt=torch.device("cpu"),
        logger=logging.getLogger(__name__),
        enable_cache=True,
    ):
        super().__init__()
        self.logger = logger
        self.device = device
        self.device_gpt = device_gpt
        self.enable_cache = enable_cache
        self.generator = torch.Generator(device=device)

        self.num_vq = int(gpt_config["num_vq"])
        self.num_audio_tokens = int(gpt_config["num_audio_tokens"])
        self.num_text_tokens = int(gpt_config["num_text_tokens"])

        self.use_flash_attn = use_flash_attn
        self.is_te_llama = False
        self.is_vllm = use_vllm

        if self.is_vllm:
            return

        self.llama_config = self._build_llama_config(gpt_config)
        self.emb_code = [ec.__call__ for ec in embed.emb_code]
        self.emb_text = embed.emb_text.__call__
        self.head_text = embed.head_text.__call__
        self.head_code = [hc.__call__ for hc in embed.head_code]

    def load_pretrained(self, gpt_folder: str, embed_file_path: str, experimental=False):
        self.gpt = LlamaModel.from_pretrained(gpt_folder).to(self.device_gpt)
        del self.gpt.embed_tokens

        if experimental and "cuda" in str(self.device_gpt):
            self.logger.warning("experimental enabled but TELlamaModel not available without CUDA/Linux")

    class Context:
        def __init__(self):
            self._interrupt = False

        def set(self, v: bool):
            self._interrupt = v

        def get(self) -> bool:
            return self._interrupt

    def _build_llama_config(self, config: dict) -> LlamaConfig:
        return LlamaConfig(**config)

    def prepare(self, compile=False):
        if self.use_flash_attn:
            self.gpt = self.gpt.to(dtype=torch.float16)
        if compile:
            try:
                self.compile(backend="inductor", dynamic=True)
                self.gpt.compile(backend="inductor", dynamic=True)
            except RuntimeError as e:
                self.logger.warning(f"compile failed: {e}. fallback to normal mode.")

    @dataclass(repr=False, eq=False)
    class _GenerationInputs:
        position_ids: torch.Tensor
        cache_position: torch.Tensor
        input_ids: Optional[torch.Tensor] = None
        past_key_values: Optional[Tuple[Tuple[torch.FloatTensor]]] = None
        attention_mask: Optional[torch.Tensor] = None
        inputs_embeds: Optional[torch.Tensor] = None

        def to(self, device: torch.device, dtype: torch.dtype):
            if self.attention_mask is not None:
                self.attention_mask = self.attention_mask.to(device, dtype=dtype)
            if self.position_ids is not None:
                self.position_ids = self.position_ids.to(device, dtype=dtype)
            if self.inputs_embeds is not None:
                self.inputs_embeds = self.inputs_embeds.to(device, dtype=dtype)
            if self.cache_position is not None:
                self.cache_position = self.cache_position.to(device, dtype=dtype)

    @torch.no_grad()
    def _prepare_generation_inputs(
        self,
        input_ids: torch.Tensor,
        past_key_values: Optional[Union[Tuple[Tuple[torch.FloatTensor]], Cache]] = None,
        attention_mask: Optional[torch.Tensor] = None,
        inputs_embeds: Optional[torch.Tensor] = None,
        cache_position: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.Tensor] = None,
    ) -> _GenerationInputs:
        has_static_cache = False
        if past_key_values is None:
            if hasattr(self.gpt.layers[0], "self_attn"):
                past_key_values = getattr(self.gpt.layers[0].self_attn, "past_key_value", None)
            has_static_cache = past_key_values is not None

        past_length = 0
        max_cache_length = None
        cache_length = 0
        if past_key_values is not None:
            if isinstance(past_key_values, Cache):
                if past_key_values.layers and len(past_key_values.layers):
                    past_length = (
                        int(cache_position[0]) if cache_position is not None
                        else past_key_values.get_seq_length()
                    )
                    try:
                        max_cache_length = past_key_values.get_max_cache_shape()
                    except:
                        max_cache_length = past_key_values.get_max_length()
                    cache_length = (
                        past_length if max_cache_length is None
                        else min(max_cache_length, past_length)
                    )
            else:
                cache_length = past_length = past_key_values[0][0].shape[2]

            if attention_mask is not None and attention_mask.shape[1] > input_ids.shape[1]:
                start = attention_mask.shape[1] - past_length
                input_ids = input_ids.narrow(1, -start, start)
            elif past_length < input_ids.shape[1]:
                input_ids = input_ids.narrow(1, past_length, input_ids.size(1) - past_length)

            if (max_cache_length is not None and max_cache_length > 0
                    and attention_mask is not None
                    and cache_length + input_ids.shape[1] > max_cache_length):
                attention_mask = attention_mask.narrow(1, -max_cache_length, max_cache_length)

        if attention_mask is not None and position_ids is None:
            position_ids = attention_mask.long().cumsum(-1) - 1
            position_ids.masked_fill_(attention_mask.eq(0), 1)
            if past_key_values:
                position_ids = position_ids.narrow(1, -input_ids.shape[1], input_ids.shape[1])

        input_length = position_ids.shape[-1] if position_ids is not None else input_ids.shape[-1]
        if cache_position is None:
            cache_position = torch.arange(past_length, past_length + input_length, device=input_ids.device)
        else:
            cache_position = cache_position.narrow(0, -input_length, input_length)

        if has_static_cache:
            past_key_values = None

        model_inputs = self._GenerationInputs(
            position_ids=position_ids,
            cache_position=cache_position,
        )

        if inputs_embeds is not None and past_key_values is None:
            model_inputs.inputs_embeds = inputs_embeds
        else:
            model_inputs.input_ids = input_ids.contiguous()

        model_inputs.past_key_values = past_key_values
        model_inputs.attention_mask = attention_mask
        return model_inputs

    @dataclass(repr=False, eq=False)
    class GenerationOutputs:
        ids: List[torch.Tensor]
        attentions: List[Optional[Tuple[torch.FloatTensor, ...]]]
        hiddens: List[torch.Tensor]

        def destroy(self):
            del_all(self.ids)
            del_all(self.attentions)
            del_all(self.hiddens)

    @torch.no_grad()
    def _prepare_generation_outputs(
        self,
        inputs_ids: torch.Tensor,
        start_idx: int,
        end_idx: torch.Tensor,
        attentions: List[Optional[Tuple[torch.FloatTensor, ...]]],
        hiddens: List[torch.Tensor],
        infer_text: bool,
    ) -> GenerationOutputs:
        end_idx_int = end_idx.int()
        inputs_ids_lst = [
            inputs_ids[idx].narrow(0, start_idx, int(i))
            for idx, i in enumerate(end_idx_int)
        ]
        if infer_text:
            inputs_ids_lst = [i.narrow(1, 0, 1).squeeze_(1) for i in inputs_ids_lst]

        hiddens_lst = []
        if len(hiddens) > 0:
            hiddens_lst = torch.stack(hiddens, 1)
            hiddens_lst = [
                hiddens_lst[idx].narrow(0, 0, int(i))
                for idx, i in enumerate(end_idx_int)
            ]

        return self.GenerationOutputs(
            ids=inputs_ids_lst,
            attentions=attentions,
            hiddens=hiddens_lst,
        )

    @torch.no_grad()
    def generate(
        self,
        emb: torch.Tensor,
        inputs_ids: torch.Tensor,
        temperature: torch.Tensor,
        eos_token: Union[int, torch.Tensor],
        attention_mask: Optional[torch.Tensor] = None,
        max_new_token=2048,
        min_new_token=0,
        logits_processors: Tuple[Callable[[torch.LongTensor, torch.FloatTensor], torch.FloatTensor]] = (),
        infer_text=False,
        return_attn=False,
        return_hidden=False,
        stream=False,
        show_tqdm=True,
        ensure_non_empty=True,
        stream_batch=24,
        manual_seed: Optional[int] = None,
        context=Context(),
    ):
        self.logger.debug("start generate")

        attentions = []
        hiddens = []
        stream_iter = 0

        start_idx, end_idx = inputs_ids.shape[1], torch.zeros(
            inputs_ids.shape[0], device=inputs_ids.device, dtype=torch.long
        )
        finish = torch.zeros(inputs_ids.shape[0], device=inputs_ids.device).bool()

        old_temperature = temperature
        temperature = (
            temperature.unsqueeze(0)
            .expand(inputs_ids.shape[0], -1)
            .contiguous()
            .view(-1, 1)
        )

        attention_mask_cache = torch.ones(
            (inputs_ids.shape[0], inputs_ids.shape[1] + max_new_token),
            dtype=torch.bool,
            device=inputs_ids.device,
        )
        if attention_mask is not None:
            attention_mask_cache.narrow(1, 0, attention_mask.shape[1]).copy_(attention_mask)

        progress = inputs_ids.size(1)
        inputs_ids_buf = torch.zeros(
            inputs_ids.size(0), progress + max_new_token, inputs_ids.size(2),
            dtype=inputs_ids.dtype, device=inputs_ids.device,
        )
        inputs_ids_buf.narrow(1, 0, progress).copy_(inputs_ids)
        del inputs_ids
        inputs_ids = inputs_ids_buf.narrow(1, 0, progress)

        pbar = None
        if show_tqdm:
            pbar = tqdm(
                total=max_new_token,
                desc="text" if infer_text else "code",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}(max) [{elapsed}, {rate_fmt}{postfix}]",
            )

        past_key_values = None

        for i in range(max_new_token):
            model_input = self._prepare_generation_inputs(
                inputs_ids,
                past_key_values,
                attention_mask_cache.narrow(1, 0, inputs_ids.shape[1]),
            )

            if i > 0:
                del emb
                inputs_ids_emb = model_input.input_ids.to(self.device_gpt)
                if infer_text:
                    emb = self.emb_text(inputs_ids_emb[:, :, 0])
                else:
                    code_emb = [
                        self.emb_code[i](inputs_ids_emb[:, :, i]).to(self.device)
                        for i in range(self.num_vq)
                    ]
                    emb = torch.stack(code_emb, 3).sum(3)
                del inputs_ids_emb, model_input.input_ids
            model_input.inputs_embeds = emb
            model_input.to(self.device_gpt, self.gpt.dtype)

            outputs = self.gpt(
                attention_mask=model_input.attention_mask,
                position_ids=model_input.position_ids,
                past_key_values=model_input.past_key_values,
                inputs_embeds=model_input.inputs_embeds,
                use_cache=self.enable_cache,
                output_attentions=return_attn,
                cache_position=model_input.cache_position,
            )
            del_all(model_input)
            attentions.append(outputs.attentions)
            hidden_states = outputs.last_hidden_state.to(self.device, dtype=torch.float)
            past_key_values = outputs.past_key_values
            del_all(outputs)

            if return_hidden:
                hiddens.append(hidden_states.narrow(1, -1, 1).squeeze_(1))

            with P.cached():
                if infer_text:
                    logits = self.head_text(hidden_states)
                else:
                    logits = torch.empty(
                        hidden_states.size(0), hidden_states.size(1),
                        self.num_audio_tokens, self.num_vq,
                        dtype=torch.float, device=self.device,
                    )
                    for num_vq_iter in range(self.num_vq):
                        x = self.head_code[num_vq_iter](hidden_states)
                        logits[..., num_vq_iter] = x
                        del x

            del hidden_states
            logits = logits.narrow(1, -1, 1).squeeze_(1).float()

            if not infer_text:
                logits = logits.permute(0, 2, 1)
                logits = logits.reshape(-1, logits.size(2))
                inputs_ids_sliced = inputs_ids.narrow(
                    1, start_idx, inputs_ids.size(1) - start_idx,
                ).permute(0, 2, 1)
                logits_token = inputs_ids_sliced.reshape(
                    inputs_ids_sliced.size(0) * inputs_ids_sliced.size(1), -1,
                ).to(self.device)
                del inputs_ids_sliced
            else:
                logits_token = (
                    inputs_ids.narrow(1, start_idx, inputs_ids.size(1) - start_idx)
                    .narrow(2, 0, 1).to(self.device)
                )

            logits /= temperature

            for logitsProcessors in logits_processors:
                logits = logitsProcessors(logits_token, logits)

            del logits_token

            if i < min_new_token:
                logits[:, eos_token] = -torch.inf

            scores = F.softmax(logits, dim=-1)
            del logits

            if manual_seed is None:
                idx_next = torch.multinomial(scores, num_samples=1).to(finish.device)
            else:
                idx_next = torch.multinomial(
                    scores, num_samples=1,
                    generator=self.generator.manual_seed(manual_seed),
                ).to(finish.device)

            del scores

            if not infer_text:
                idx_next = idx_next.view(-1, self.num_vq)
                finish_or = idx_next.eq(eos_token).any(1)
                finish.logical_or_(finish_or)
                del finish_or
                inputs_ids_buf.narrow(1, progress, 1).copy_(idx_next.unsqueeze_(1))
            else:
                finish_or = idx_next.eq(eos_token).any(1)
                finish.logical_or_(finish_or)
                del finish_or
                inputs_ids_buf.narrow(1, progress, 1).copy_(
                    idx_next.unsqueeze_(-1).expand(-1, -1, self.num_vq),
                )

            if i == 0 and finish.any():
                self.logger.warning(
                    "unexpected end at index %s",
                    str([unexpected_idx.item() for unexpected_idx in finish.nonzero()]),
                )
                if ensure_non_empty and manual_seed is None:
                    if show_tqdm:
                        pbar.close()
                    self.logger.warning("regenerate in order to ensure non-empty")
                    del_all(attentions)
                    del_all(hiddens)
                    del start_idx, end_idx, finish, temperature, attention_mask_cache, past_key_values, idx_next, inputs_ids_buf
                    new_gen = self.generate(
                        emb, inputs_ids, old_temperature, eos_token, attention_mask,
                        max_new_token, min_new_token, logits_processors, infer_text,
                        return_attn, return_hidden, stream, show_tqdm, ensure_non_empty,
                        stream_batch, manual_seed, context,
                    )
                    for result in new_gen:
                        yield result
                    del inputs_ids
                return

            del idx_next
            progress += 1
            inputs_ids = inputs_ids_buf.narrow(1, 0, progress)

            not_finished = finish.logical_not().to(end_idx.device)
            end_idx.add_(not_finished.int())
            stream_iter += not_finished.any().int()

            if stream and stream_iter > 0 and stream_iter % stream_batch == 0:
                yield self._prepare_generation_outputs(
                    inputs_ids, start_idx, end_idx, attentions, hiddens, infer_text,
                )
            del not_finished

            if finish.all() or context.get():
                break

            if pbar is not None:
                pbar.update(1)

        if pbar is not None:
            pbar.close()

        if not finish.all():
            if context.get():
                self.logger.warning("generation is interrupted")
            else:
                self.logger.warning(f"incomplete result. hit max_new_token: {max_new_token}")

        del finish, inputs_ids_buf

        yield self._prepare_generation_outputs(
            inputs_ids, start_idx, end_idx, attentions, hiddens, infer_text,
        )
