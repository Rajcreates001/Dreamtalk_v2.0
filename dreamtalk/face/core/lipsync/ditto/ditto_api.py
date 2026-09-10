import librosa
import math
import numpy as np
import torch
import os
import subprocess
import logging
from typing import Optional, Dict, Any
from .config import DittoConfig

logger = logging.getLogger("dreamtalk.face.ditto")


class DittoAPI:
    def __init__(self, config: Optional[DittoConfig] = None):
        self.config = config or DittoConfig()
        self.sdk = None

    def load_models(self):
        from stream_pipeline_offline import StreamSDK
        self.sdk = StreamSDK(self.config.cfg_pkl, self.config.data_root)
        logger.info("Ditto models loaded")

    def preprocess_audio(self, audio_path: str, target_sr: int = 16000) -> str:
        processed = audio_path.rsplit(".", 1)[0] + "_ditto.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "warning",
             "-i", audio_path,
             "-ar", str(target_sr),
             "-ac", "1",
             "-sample_fmt", "s16",
             processed],
            check=True,
        )
        return processed

    def generate(
        self,
        audio_path: str,
        source_path: str,
        output_path: str,
        more_kwargs: Optional[Dict] = None,
        enhance_audio: bool = True,
    ) -> Dict[str, Any]:
        if self.sdk is None:
            raise RuntimeError("Models not loaded. Call load_models() first.")

        if more_kwargs is None:
            more_kwargs = {}

        if enhance_audio:
            audio_path = self.preprocess_audio(audio_path)

        setup_kwargs = more_kwargs.get("setup_kwargs", {})
        run_kwargs = more_kwargs.get("run_kwargs", {})

        self.sdk.setup(source_path, output_path, **setup_kwargs)

        audio, sr = librosa.core.load(audio_path, sr=16000)
        num_f = math.ceil(len(audio) / 16000 * 25)

        fade_in = run_kwargs.get("fade_in", -1)
        fade_out = run_kwargs.get("fade_out", -1)
        ctrl_info = run_kwargs.get("ctrl_info", {})
        self.sdk.setup_Nd(N_d=num_f, fade_in=fade_in, fade_out=fade_out, ctrl_info=ctrl_info)

        if self.config.online:
            chunksize = run_kwargs.get("chunksize", (3, 5, 2))
            audio = np.concatenate([np.zeros((chunksize[0] * 640,), dtype=np.float32), audio], 0)
            split_len = int(sum(chunksize) * 0.04 * 16000) + 80
            for i in range(0, len(audio), chunksize[1] * 640):
                audio_chunk = audio[i:i + split_len]
                if len(audio_chunk) < split_len:
                    audio_chunk = np.pad(audio_chunk, (0, split_len - len(audio_chunk)), mode="constant")
                self.sdk.run_chunk(audio_chunk, chunksize)
        else:
            aud_feat = self.sdk.wav2feat.wav2feat(audio)
            self.sdk.audio2motion_queue.put(aud_feat)

        self.sdk.close()

        temp_output = self.sdk.tmp_output_path
        if self.config.use_hw_encoder and torch.cuda.is_available():
            final_output = output_path.rsplit(".", 1)[0] + "_final.mp4"
            subprocess.run(
                ["ffmpeg", "-y", "-v", "warning",
                 "-i", temp_output,
                 "-i", audio_path,
                 "-map", "0:v:0",
                 "-map", "1:a:0",
                 "-c:v", "h264_nvenc",
                 "-preset", "p4",
                 "-c:a", "aac",
                 "-shortest",
                 final_output],
                check=True,
            )
        else:
            cmd = (
                f'ffmpeg -loglevel error -y -i "{temp_output}" '
                f'-i "{audio_path}" -map 0:v -map 1:a '
                f'-c:v copy -c:a aac "{output_path}"'
            )
            os.system(cmd)
            final_output = output_path

        return {"video_path": final_output, "audio_path": audio_path, "source_path": source_path}
