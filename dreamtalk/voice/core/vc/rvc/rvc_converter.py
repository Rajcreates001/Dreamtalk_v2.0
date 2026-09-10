"""RVC (Retrieval-based Voice Conversion) Converter.

Provides the high-level RVCConverter that wraps the full rvc_api.RVC engine.
Uses real downloaded weights from weights/voice/rvc/.
Falls back gracefully if weights aren't loaded.
"""

import os
import pathlib
import shutil
import logging
import numpy as np
from typing import Optional

import torch

logger = logging.getLogger("dreamtalk.voice.vc.rvc")

# ── Project root detection ────────────────────────────────────────
# rvc_converter.py is at voice/core/vc/rvc/rvc_converter.py -> 5 levels up
_RVC_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent.parent
_RVC_WEIGHTS_DIR = _RVC_ROOT / "weights" / "voice" / "rvc"
_RVC_HUBERT_PATH = str(_RVC_WEIGHTS_DIR / "hubert_base.pt")
_RVC_RMVPE_PATH = str(_RVC_WEIGHTS_DIR / "rmvpe.pt")
_RVC_PRETRAINED_DIR = _RVC_WEIGHTS_DIR / "pretrained_v2"

_RVC_PRETRAINED_PATHS = {
    "f0G48k": str(_RVC_PRETRAINED_DIR / "f0G48k.pth"),
    "f0D48k": str(_RVC_PRETRAINED_DIR / "f0D48k.pth"),
    "f0G40k": str(_RVC_PRETRAINED_DIR / "f0G40k.pth"),
    "f0D40k": str(_RVC_PRETRAINED_DIR / "f0D40k.pth"),
}


def get_best_pretrained_path() -> Optional[str]:
    if os.path.exists(_RVC_PRETRAINED_PATHS["f0G48k"]):
        return _RVC_PRETRAINED_PATHS["f0G48k"]
    if os.path.exists(_RVC_PRETRAINED_PATHS["f0G40k"]):
        return _RVC_PRETRAINED_PATHS["f0G40k"]
    return None


def check_weights_available() -> dict:
    return {
        "hubert_base.pt": os.path.exists(_RVC_HUBERT_PATH),
        "rmvpe.pt": os.path.exists(_RVC_RMVPE_PATH),
        "pretrained_v2/f0G48k.pth": os.path.exists(_RVC_PRETRAINED_PATHS["f0G48k"]),
        "pretrained_v2/f0D48k.pth": os.path.exists(_RVC_PRETRAINED_PATHS["f0D48k"]),
        "pretrained_v2/f0G40k.pth": os.path.exists(_RVC_PRETRAINED_PATHS["f0G40k"]),
        "pretrained_v2/f0D40k.pth": os.path.exists(_RVC_PRETRAINED_PATHS["f0D40k"]),
    }


class RVCConverter:
    """RVC-style voice conversion engine.

    Supports:
    - Voice conversion from source speaker to target speaker
    - Pitch shifting
    - Formant preservation
    - Uses the full rvc_api.RVC class when available
    """

    def __init__(self, model_path: Optional[str] = None, device: str = "cpu"):
        self.model_path = model_path
        self.device = device
        self._rvc_api = None
        self._loaded = False
        self._hubert_path = _RVC_HUBERT_PATH
        self._rmvpe_path = _RVC_RMVPE_PATH
        self._generator_path = model_path or get_best_pretrained_path()

        if self._generator_path and os.path.exists(self._generator_path):
            self.load_model(self._generator_path)

    def load_model(self, generator_path: str):
        try:
            from voice.core.vc.rvc.rvc_api import RVC as RealRVC
        except ImportError:
            try:
                from dreamtalk.voice.core.vc.rvc.rvc_api import RVC as RealRVC
            except ImportError:
                RealRVC = None
        try:
            if RealRVC is None:
                raise ImportError("RVC API not found")

            has_fairseq = False
            try:
                import fairseq
                has_fairseq = True
            except ImportError:
                logger.warning("fairseq not installed - HuBERT model cannot load")

            if not has_fairseq:
                logger.warning("fairseq missing - falling back to basic RVC")
                self._loaded = False
                return

            if not os.path.exists(self._hubert_path):
                logger.warning("HuBERT weights missing at %s", self._hubert_path)
                self._loaded = False
                return

            self._rvc_api = RealRVC(
                pth_path=generator_path,
                device=self.device,
                is_half=False,
                f0_method="rmvpe" if os.path.exists(self._rmvpe_path) else "harvest",
            )
            self._loaded = True
            logger.info(
                "RVC engine loaded: hubert=%s, generator=%s, rmvpe=%s",
                os.path.basename(self._hubert_path),
                os.path.basename(generator_path),
                os.path.exists(self._rmvpe_path),
            )

        except ImportError as e:
            logger.warning("RVC engine import failed: %s", e)
            self._loaded = False
        except Exception as e:
            logger.warning("RVC engine load failed: %s", e)
            self._loaded = False

    def convert(
        self,
        audio_path: str,
        target_speaker: str = "default",
        output_path: Optional[str] = None,
        pitch_adjust: int = 0,
    ) -> Optional[str]:
        if output_path is None:
            base, ext = os.path.splitext(os.path.basename(audio_path))
            output_path = os.path.join(
                os.path.dirname(audio_path),
                f"{base}_rvc_{target_speaker}{ext}",
            )

        if not self._loaded or self._rvc_api is None:
            logger.warning("RVC not loaded - passthrough (no voice conversion)")
            return self._passthrough(audio_path, output_path, pitch_adjust)

        try:
            import soundfile as sf
            audio, sr = sf.read(audio_path)
            if sr != 16000:
                import librosa
                audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
                sr = 16000
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)

            self._rvc_api.f0_up_key = float(pitch_adjust)
            audio_tensor = torch.from_numpy(audio).float().to(self._rvc_api.device)
            output_audio = self._rvc_api.infer(audio_tensor, f0method="rmvpe")

            sf.write(output_path, output_audio, self._rvc_api.tgt_sr)
            logger.info("RVC conversion complete: %s", output_path)
            return output_path

        except Exception as e:
            logger.error("RVC conversion failed: %s", e)
            return self._passthrough(audio_path, output_path, pitch_adjust)

    def _passthrough(self, audio_path: str, output_path: str, pitch_adjust: int = 0) -> str:
        try:
            import soundfile as sf
            audio, sr = sf.read(audio_path)
            if pitch_adjust != 0:
                import librosa
                factor = 2.0 ** (pitch_adjust / 12.0)
                new_sr = int(sr * factor)
                audio = librosa.resample(audio, orig_sr=sr, target_sr=new_sr)
                sr = new_sr
            sf.write(output_path, audio, sr)
        except Exception as e:
            logger.error("Passthrough failed: %s", e)
            shutil.copy2(audio_path, output_path)
        return output_path

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def tgt_sr(self) -> int:
        return self._rvc_api.tgt_sr if self._rvc_api else 24000
