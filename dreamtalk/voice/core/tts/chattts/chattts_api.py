# Dreamtalk - Voice Engine
# Extracted from ChatTTS

import os
import re
import logging
from dataclasses import dataclass, asdict
from typing import Literal, Optional, List, Tuple, Dict, Union
from json import load
from pathlib import Path

import numpy as np
import torch
from vocos import Vocos
from vocos.pretrained import instantiate_class

from .config import Config
from .dvae import DVAE
from .embed import Embed
from .gpt import GPT
from .processors import gen_logits
from .tokenizer import Tokenizer
from .speaker import Speaker
from .utils import load_safetensors, select_device, del_all

try:
    from .norm import Normalizer as _Normalizer
    _has_normalizer = True
except ImportError:
    _has_normalizer = False


class Chat:
    def __init__(self, logger=logging.getLogger(__name__)):
        self.logger = logger
        self.config = Config()

        if _has_normalizer:
            self.normalizer = _Normalizer(
                os.path.join(os.path.dirname(__file__), "res", "homophones_map.json"),
                logger,
            )
        else:
            self.normalizer = None

        sha256_path = os.path.join(os.path.dirname(__file__), "res", "sha256_map.json")
        if os.path.exists(sha256_path):
            with open(sha256_path) as f:
                self.sha256_map: Dict[str, str] = load(f)
        else:
            self.sha256_map = {}

        self.context = GPT.Context()

    def has_loaded(self, use_decoder=False):
        not_finish = False
        check_list = ["vocos", "gpt", "tokenizer", "embed"]
        if use_decoder:
            check_list.append("decoder")
        else:
            check_list.append("dvae")
        for module in check_list:
            if not hasattr(self, module):
                self.logger.warning(f"{module} not initialized.")
                not_finish = True
        return not not_finish

    def load(
        self,
        vocos_ckpt_path: str = None,
        dvae_ckpt_path: str = None,
        gpt_ckpt_path: str = None,
        embed_path: str = None,
        decoder_ckpt_path: str = None,
        tokenizer_path: str = None,
        compile: bool = False,
        device: Optional[torch.device] = None,
        coef: Optional[str] = None,
        use_flash_attn=False,
        enable_cache=True,
    ) -> bool:
        return self._load(
            vocos_ckpt_path=vocos_ckpt_path,
            dvae_ckpt_path=dvae_ckpt_path,
            gpt_ckpt_path=gpt_ckpt_path,
            embed_path=embed_path,
            decoder_ckpt_path=decoder_ckpt_path,
            tokenizer_path=tokenizer_path,
            compile=compile,
            device=device,
            coef=coef,
            use_flash_attn=use_flash_attn,
            enable_cache=enable_cache,
        )

    def unload(self):
        logger = self.logger
        if self.normalizer is not None:
            self.normalizer.destroy()
            del self.normalizer
        del self.sha256_map
        del_list = ["vocos", "gpt", "decoder", "dvae", "tokenizer", "embed"]
        for module in del_list:
            if hasattr(self, module):
                delattr(self, module)
        self.__init__(logger)

    def sample_random_speaker(self) -> str:
        return self.speaker.sample_random()

    def sample_audio_speaker(self, wav: Union[np.ndarray, torch.Tensor]) -> str:
        return self.speaker.encode_prompt(self.dvae.sample_audio(wav))

    @dataclass(repr=False, eq=False)
    class RefineTextParams:
        prompt: str = ""
        top_P: float = 0.7
        top_K: int = 20
        temperature: float = 0.7
        repetition_penalty: float = 1.0
        max_new_token: int = 384
        min_new_token: int = 0
        show_tqdm: bool = True
        ensure_non_empty: bool = True
        manual_seed: Optional[int] = None

    @dataclass(repr=False, eq=False)
    class InferCodeParams(RefineTextParams):
        prompt: str = "[speed_5]"
        spk_emb: Optional[str] = None
        spk_smp: Optional[str] = None
        txt_smp: Optional[str] = None
        temperature: float = 0.3
        repetition_penalty: float = 1.05
        max_new_token: int = 2048
        stream_batch: int = 24
        stream_speed: int = 12000
        pass_first_n_batches: int = 2

    def infer(
        self,
        text,
        stream=False,
        lang=None,
        skip_refine_text=False,
        refine_text_only=False,
        use_decoder=True,
        do_text_normalization=True,
        do_homophone_replacement=True,
        split_text=True,
        max_split_batch=4,
        params_refine_text=RefineTextParams(),
        params_infer_code=InferCodeParams(),
    ):
        self.context.set(False)

        if split_text and isinstance(text, str):
            if "\n" in text:
                text = text.split("\n")
            else:
                text = re.split(r"(?<=。)|(?<=\.\s)", text)
                nt = []
                if isinstance(text, list):
                    for t in text:
                        if t:
                            nt.append(t)
                    text = nt
                else:
                    text = [text]
            self.logger.info("split text into %d parts", len(text))

        if len(text) == 0:
            return []

        res_gen = self._infer(
            text, stream, lang, skip_refine_text, refine_text_only,
            use_decoder, do_text_normalization, do_homophone_replacement,
            split_text, max_split_batch, params_refine_text, params_infer_code,
        )
        if stream:
            return res_gen
        elif not refine_text_only:
            stripped_wavs = []
            thr = np.float32(1e-5)
            for wavs in res_gen:
                for wav in wavs:
                    stripped_wavs.append(wav[np.abs(wav) > thr])
            if split_text:
                return [np.concatenate(stripped_wavs)]
            return stripped_wavs
        else:
            return next(res_gen)

    def interrupt(self):
        self.context.set(True)

    @torch.no_grad()
    def _load(
        self,
        vocos_ckpt_path: str = None,
        dvae_ckpt_path: str = None,
        gpt_ckpt_path: str = None,
        embed_path: str = None,
        decoder_ckpt_path: str = None,
        tokenizer_path: str = None,
        device: Optional[torch.device] = None,
        compile: bool = False,
        coef: Optional[str] = None,
        use_flash_attn=False,
        enable_cache=True,
    ):
        if device is None:
            device = select_device()
            self.logger.info("use device %s", str(device))
        self.device = device
        self.device_gpt = device if "mps" not in str(device) else torch.device("cpu")
        self.compile = compile

        feature_extractor = instantiate_class(
            args=(), init=asdict(self.config.vocos.feature_extractor)
        )
        backbone = instantiate_class(args=(), init=asdict(self.config.vocos.backbone))
        head = instantiate_class(args=(), init=asdict(self.config.vocos.head))
        vocos = (
            Vocos(feature_extractor=feature_extractor, backbone=backbone, head=head)
            .to("cpu" if "mps" in str(device) or "npu" in str(device) else device)
            .eval()
        )
        assert vocos_ckpt_path, "vocos_ckpt_path should not be None"
        vocos.load_state_dict(load_safetensors(vocos_ckpt_path))
        self.vocos = vocos
        self.logger.log(logging.INFO, "vocos loaded.")

        dvae_device = torch.device("cpu") if "npu" in str(self.device) else device
        dvae = DVAE(
            decoder_config=asdict(self.config.dvae.decoder),
            encoder_config=asdict(self.config.dvae.encoder),
            vq_config=asdict(self.config.dvae.vq),
            dim=self.config.dvae.decoder.idim,
            coef=coef,
            device=dvae_device,
        )
        coef = str(dvae)
        assert dvae_ckpt_path, "dvae_ckpt_path should not be None"
        dvae.load_pretrained(dvae_ckpt_path, dvae_device)
        self.dvae = dvae.eval()
        self.logger.log(logging.INFO, "dvae loaded.")

        embed = Embed(
            self.config.embed.hidden_size,
            self.config.embed.num_audio_tokens,
            self.config.embed.num_text_tokens,
            self.config.embed.num_vq,
        )
        embed.load_pretrained(embed_path, device=device)
        self.embed = embed.to(device)
        self.logger.log(logging.INFO, "embed loaded.")

        gpt = GPT(
            gpt_config=asdict(self.config.gpt),
            embed=self.embed,
            use_flash_attn=use_flash_attn,
            device=device,
            device_gpt=self.device_gpt,
            logger=self.logger,
            enable_cache=enable_cache,
        ).eval()
        assert gpt_ckpt_path, "gpt_ckpt_path should not be None"
        gpt.load_pretrained(gpt_ckpt_path, embed_path)
        gpt.prepare(compile=compile and "cuda" in str(device))
        self.gpt = gpt
        self.logger.log(logging.INFO, "gpt loaded.")

        self.speaker = Speaker(
            self.config.gpt.hidden_size, self.config.spk_stat, device
        )
        self.logger.log(logging.INFO, "speaker loaded.")

        decoder = DVAE(
            decoder_config=asdict(self.config.decoder),
            dim=self.config.decoder.idim,
            coef=coef,
            device=device,
        )
        coef = str(decoder)
        assert decoder_ckpt_path, "decoder_ckpt_path should not be None"
        decoder.load_pretrained(decoder_ckpt_path, device)
        self.decoder = decoder.eval()
        self.logger.log(logging.INFO, "decoder loaded.")

        if tokenizer_path:
            self.tokenizer = Tokenizer(tokenizer_path)
            self.logger.log(logging.INFO, "tokenizer loaded.")

        self.coef = coef
        return self.has_loaded()

    def _infer(
        self,
        text: Union[List[str], str],
        stream=False,
        lang=None,
        skip_refine_text=False,
        refine_text_only=False,
        use_decoder=True,
        do_text_normalization=True,
        do_homophone_replacement=True,
        split_text=True,
        max_split_batch=4,
        params_refine_text=RefineTextParams(),
        params_infer_code=InferCodeParams(),
    ):
        assert self.has_loaded(use_decoder=use_decoder)

        if not isinstance(text, list):
            text = [text]

        if self.normalizer is not None:
            text = [
                self.normalizer(t, do_text_normalization, do_homophone_replacement, lang)
                for t in text
            ]

        if not skip_refine_text:
            refined = self._refine_text(text, self.device, params_refine_text)
            text_tokens = refined.ids
            text_tokens = [i[i.less(self.tokenizer.break_0_ids)] for i in text_tokens]
            text = self.tokenizer.decode(text_tokens)
            self.logger.debug("refined texts %s", str(text))
            refined.destroy()
            if refine_text_only:
                if split_text and isinstance(text, list):
                    text = "\n".join(text)
                yield text
                return

        if split_text and len(text) > 1 and params_infer_code.spk_smp is None:
            refer_text = text[0]
            result = next(
                self._infer_code(refer_text, False, self.device, use_decoder, params_infer_code)
            )
            wavs = self._decode_to_wavs(
                result.hiddens if use_decoder else result.ids, use_decoder,
            )
            result.destroy()
            assert len(wavs), 1
            params_infer_code.spk_smp = self.sample_audio_speaker(wavs[0])
            params_infer_code.txt_smp = refer_text

        if stream:
            length = 0
            pass_batch_count = 0
        if split_text:
            n = len(text) // max_split_batch
            if len(text) % max_split_batch:
                n += 1
        else:
            n = 1
            max_split_batch = len(text)
        for i in range(n):
            text_remain = text[i * max_split_batch:]
            if len(text_remain) > max_split_batch:
                text_remain = text_remain[:max_split_batch]
            if split_text:
                self.logger.info(
                    "infer split %d~%d",
                    i * max_split_batch, i * max_split_batch + len(text_remain),
                )
            for result in self._infer_code(
                text_remain, stream, self.device, use_decoder, params_infer_code,
            ):
                wavs = self._decode_to_wavs(
                    result.hiddens if use_decoder else result.ids, use_decoder,
                )
                result.destroy()
                if stream:
                    pass_batch_count += 1
                    if pass_batch_count <= params_infer_code.pass_first_n_batches:
                        continue
                    a = length
                    b = a + params_infer_code.stream_speed
                    if b > wavs.shape[1]:
                        b = wavs.shape[1]
                    new_wavs = wavs[:, a:b]
                    length = b
                    yield new_wavs
                else:
                    yield wavs
            if stream:
                new_wavs = wavs[:, length:]
                keep_cols = np.sum(np.abs(new_wavs) > 1e-5, axis=0) > 0
                yield new_wavs[:][:, keep_cols]

    @torch.inference_mode()
    def _vocos_decode(self, spec: torch.Tensor) -> np.ndarray:
        if "mps" in str(self.device) or "npu" in str(self.device):
            return self.vocos.decode(spec.cpu()).cpu().numpy()
        else:
            return self.vocos.decode(spec).cpu().numpy()

    @torch.inference_mode()
    def _decode_to_wavs(self, result_list: List[torch.Tensor], use_decoder: bool):
        decoder = self.decoder if use_decoder else self.dvae
        max_x_len = -1
        if len(result_list) == 0:
            return np.array([], dtype=np.float32)
        for result in result_list:
            if result.size(0) > max_x_len:
                max_x_len = result.size(0)
        batch_result = torch.zeros(
            (len(result_list), result_list[0].size(1), max_x_len),
            dtype=result_list[0].dtype, device=result_list[0].device,
        )
        for i in range(len(result_list)):
            src = result_list[i]
            batch_result[i].narrow(1, 0, src.size(0)).copy_(src.permute(1, 0))
            del src
        del_all(result_list)
        mel_specs = decoder(batch_result)
        del batch_result
        wavs = self._vocos_decode(mel_specs)
        del mel_specs
        return wavs

    @torch.no_grad()
    def _infer_code(
        self,
        text: Tuple[List[str], str],
        stream: bool,
        device: torch.device,
        return_hidden: bool,
        params: InferCodeParams,
    ):
        gpt = self.gpt
        if not isinstance(text, list):
            text = [text]
        assert len(text), "text should not be empty"

        if not isinstance(params.temperature, list):
            temperature = [params.temperature] * self.config.gpt.num_vq
        else:
            temperature = params.temperature

        input_ids, attention_mask, text_mask = self.tokenizer.encode(
            self.speaker.decorate_code_prompts(
                text, params.prompt, params.txt_smp, params.spk_emb,
            ),
            self.config.gpt.num_vq,
            prompt=(
                self.speaker.decode_prompt(params.spk_smp)
                if params.spk_smp is not None else None
            ),
            device=self.device_gpt,
        )
        start_idx = input_ids.shape[-2]
        num_code = self.config.gpt.num_audio_tokens - 1

        logits_warpers, logits_processors = gen_logits(
            num_code=num_code,
            top_P=params.top_P,
            top_K=params.top_K,
            repetition_penalty=params.repetition_penalty,
        )

        emb = self.embed(input_ids, text_mask)
        del text_mask

        if params.spk_emb is not None:
            self.speaker.apply(
                emb, params.spk_emb, input_ids,
                self.tokenizer.spk_emb_ids, self.gpt.device_gpt,
            )

        result = gpt.generate(
            emb, input_ids,
            temperature=torch.tensor(temperature, device=device),
            eos_token=num_code,
            attention_mask=attention_mask,
            max_new_token=params.max_new_token,
            min_new_token=params.min_new_token,
            logits_processors=(*logits_processors, *logits_warpers),
            infer_text=False,
            return_hidden=return_hidden,
            stream=stream,
            show_tqdm=params.show_tqdm,
            ensure_non_empty=params.ensure_non_empty,
            stream_batch=params.stream_batch,
            manual_seed=params.manual_seed,
            context=self.context,
        )

        del emb, input_ids
        return result

    @torch.no_grad()
    def _refine_text(
        self,
        text: str,
        device: torch.device,
        params: RefineTextParams,
    ):
        gpt = self.gpt
        if not isinstance(text, list):
            text = [text]

        input_ids, attention_mask, text_mask = self.tokenizer.encode(
            self.speaker.decorate_text_prompts(text, params.prompt),
            self.config.gpt.num_vq,
            device=self.device_gpt,
        )

        logits_warpers, logits_processors = gen_logits(
            num_code=self.tokenizer.len,
            top_P=params.top_P,
            top_K=params.top_K,
            repetition_penalty=params.repetition_penalty,
        )

        emb = self.embed(input_ids, text_mask)
        del text_mask

        result = next(
            gpt.generate(
                emb, input_ids,
                temperature=torch.tensor([params.temperature], device=device),
                eos_token=self.tokenizer.eos_token,
                attention_mask=attention_mask,
                max_new_token=params.max_new_token,
                min_new_token=params.min_new_token,
                logits_processors=(*logits_processors, *logits_warpers),
                infer_text=True,
                stream=False,
                show_tqdm=params.show_tqdm,
                ensure_non_empty=params.ensure_non_empty,
                manual_seed=params.manual_seed,
                context=self.context,
            )
        )

        del emb, input_ids
        return result
