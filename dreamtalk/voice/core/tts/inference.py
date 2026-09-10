# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: GPT_SoVITS/inference_cli.py + inference_webui.py (get_tts_wav)

import os
import soundfile as sf
from typing import Optional, Tuple
from .tts_pipeline import TTS, TTS_Config
from .i18n import I18nAuto

i18n = I18nAuto()


class DreamtalkTTS:
    def __init__(self, configs: Optional[dict] = None):
        self.config = TTS_Config(configs)
        self.engine = TTS(self.config)

    def synthesize(
        self,
        ref_audio_path: str,
        ref_text: str,
        ref_language: str,
        text: str,
        text_language: str,
        top_p: float = 1,
        temperature: float = 1,
        top_k: int = 15,
        speed_factor: float = 1.0,
        sample_steps: int = 32,
        super_sampling: bool = False,
        text_split_method: str = "cut1",
        seed: int = -1,
        repetition_penalty: float = 1.35,
        parallel_infer: bool = True,
    ) -> Tuple[int, list]:
        inputs = {
            "text": text,
            "text_lang": i18n(text_language),
            "ref_audio_path": ref_audio_path,
            "prompt_text": ref_text,
            "prompt_lang": i18n(ref_language),
            "top_k": top_k,
            "top_p": top_p,
            "temperature": temperature,
            "text_split_method": text_split_method,
            "batch_size": 1,
            "speed_factor": speed_factor,
            "seed": seed,
            "parallel_infer": parallel_infer,
            "repetition_penalty": repetition_penalty,
            "sample_steps": sample_steps,
            "super_sampling": super_sampling,
            "return_fragment": False,
            "streaming_mode": False,
        }
        result_list = list(self.engine.run(inputs))
        if result_list:
            last_sampling_rate, last_audio_data = result_list[-1]
            return last_sampling_rate, last_audio_data
        return 24000, []

    def synthesize_to_file(
        self,
        ref_audio_path: str,
        ref_text: str,
        ref_language: str,
        text: str,
        text_language: str,
        output_path: str,
        **kwargs,
    ) -> str:
        sr, audio_data = self.synthesize(
            ref_audio_path=ref_audio_path,
            ref_text=ref_text,
            ref_language=ref_language,
            text=text,
            text_language=text_language,
            **kwargs,
        )
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        sf.write(output_path, audio_data, sr)
        return output_path

    def load_models(self, gpt_path: str, sovits_path: str):
        self.engine.init_t2s_weights(gpt_path)
        self.engine.init_vits_weights(sovits_path)
