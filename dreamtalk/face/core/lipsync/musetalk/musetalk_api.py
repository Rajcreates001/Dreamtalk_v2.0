import os
import torch
import logging
import subprocess
import numpy as np
from typing import Optional, Dict, Any
from pathlib import Path

from .config import MuseTalkConfig
from .inference import MuseTalkInference

logger = logging.getLogger("dreamtalk.face.musetalk")


class MuseTalkAPI:
    def __init__(self, config: Optional[MuseTalkConfig] = None):
        self.config = config or MuseTalkConfig()
        self.inference_engine = MuseTalkInference(config=self.config)
        self._loaded = False
        self._device = None

    def load_models(self):
        self._device = torch.device(
            f"cuda:{self.config.gpu_id}" if torch.cuda.is_available() else "cpu"
        )
        self.inference_engine.load_models(
            unet_model_path=self.config.unet_model_path,
            vae_type=self.config.vae_type,
            unet_config=self.config.unet_config,
            whisper_dir=self.config.whisper_dir,
            device=self._device,
            use_float16=self.config.use_float16,
            version=self.config.version,
        )
        self._loaded = True
        logger.info(
            f"MuseTalk models loaded on {self._device} "
            f"(fp16={self.config.use_float16}, version={self.config.version})"
        )

    def auto_detect_batch_size(self, target_mb: int = 512) -> int:
        if not torch.cuda.is_available():
            return 4
        try:
            total = torch.cuda.get_device_properties(0).total_memory
            free, _ = torch.cuda.mem_get_info(0)
            available_mb = free / 1024 / 1024
            batch_size = max(1, int(available_mb / target_mb))
            logger.info(f"Auto batch size: {batch_size} (available VRAM: {available_mb:.0f}MB)")
            return min(batch_size, 32)
        except Exception:
            return 8

    def encode_video(
        self,
        input_pattern: str,
        output_path: str,
        fps: float = 25,
        audio_path: Optional[str] = None,
        crf: int = 18,
        hwaccel: bool = True,
    ) -> str:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        codec = "h264_nvenc" if (hwaccel and torch.cuda.is_available()) else "libx264"
        preset = "p4" if codec == "h264_nvenc" else "medium"
        cmd = [
            "ffmpeg", "-y", "-v", "warning",
            "-r", str(fps),
            "-f", "image2",
            "-i", input_pattern,
            "-vcodec", codec,
            "-preset", preset,
            "-vf", "format=yuv420p",
            "-crf", str(crf),
        ]
        if audio_path and os.path.exists(audio_path):
            temp_video = output_path + ".tmp.mp4"
            cmd.append(temp_video)
        else:
            cmd.append(output_path)
        subprocess.run(cmd, check=True)
        if audio_path and os.path.exists(audio_path):
            cmd2 = [
                "ffmpeg", "-y", "-v", "warning",
                "-i", temp_video,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                output_path,
            ]
            subprocess.run(cmd2, check=True)
            os.remove(temp_video)
        return output_path

    def compress_audio(self, audio_path: str, target_sr: int = 16000) -> str:
        compressed = audio_path.rsplit(".", 1)[0] + "_16k.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "warning",
             "-i", audio_path,
             "-ar", str(target_sr),
             "-ac", "1",
             compressed],
            check=True,
        )
        return compressed

    @torch.no_grad()
    def generate(
        self,
        video_path: str,
        audio_path: str,
        bbox_shift: Optional[int] = None,
        fps: Optional[float] = None,
        batch_size: Optional[int] = None,
        extra_margin: Optional[int] = None,
        parsing_mode: Optional[str] = None,
        version: Optional[str] = None,
        audio_padding_length_left: Optional[int] = None,
        audio_padding_length_right: Optional[int] = None,
        result_dir: Optional[str] = None,
        output_vid_name: Optional[str] = None,
        use_saved_coord: bool = False,
        saved_coord: bool = False,
        enable_face_enhance: bool = False,
        hw_video_encode: bool = True,
    ) -> Dict[str, Any]:
        if not self._loaded:
            raise RuntimeError("Models not loaded. Call load_models() first.")

        if batch_size is None:
            batch_size = self.auto_detect_batch_size()

        audio_16k = self.compress_audio(audio_path)

        output_path = self.inference_engine.inference(
            video_path=video_path,
            audio_path=audio_16k,
            bbox_shift=bbox_shift if bbox_shift is not None else self.config.bbox_shift,
            fps=fps if fps is not None else self.config.fps,
            batch_size=batch_size,
            extra_margin=extra_margin if extra_margin is not None else self.config.extra_margin,
            parsing_mode=parsing_mode if parsing_mode is not None else self.config.parsing_mode,
            version=version if version is not None else self.config.version,
            audio_padding_length_left=audio_padding_length_left if audio_padding_length_left is not None else self.config.audio_padding_length_left,
            audio_padding_length_right=audio_padding_length_right if audio_padding_length_right is not None else self.config.audio_padding_length_right,
            result_dir=result_dir if result_dir is not None else self.config.result_dir,
            output_vid_name=output_vid_name,
            use_saved_coord=use_saved_coord or self.config.use_saved_coord,
            saved_coord=saved_coord or self.config.saved_coord,
            hw_video_encode=hw_video_encode and torch.cuda.is_available(),
        )

        if audio_16k != audio_path and os.path.exists(audio_16k):
            os.remove(audio_16k)

        return {"video_path": output_path, "audio_path": audio_path, "video_source": video_path}
