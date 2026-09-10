# GPU Code Audit Report

> **Last Updated: July 2026 — GPU fixes applied.**
> A shared device utility was created at `dreamtalk/shared/utils/device.py` that
> respects the `DREAMTALK_DEVICE` env var and auto-detects CUDA/MPS/CPU.

## ✅ Fixed Items

### Shared Device Utility
- **Added** `dreamtalk/shared/utils/device.py` with `get_device()` / `get_torch_device()`
- Respects `DREAMTALK_DEVICE` environment variable override
- Auto-detects: CUDA → MPS → CPU

### Config Files — Changed `device="cuda"` to use auto-detection
- `dreamtalk/face/core/lipsync/ditto/config.py` — now reads `DREAMTALK_DEVICE` env or falls back to auto-detect
- `dreamtalk/avatar/core/body/mhr/config.py` — same pattern
- `dreamtalk/face/core/animation/liveavatar/config.py` — same pattern

### Function Defaults — Changed `device="cuda"` → `device=None` with auto-detect
- `dreamtalk/face/core/lipsync/ditto/core/utils/load_model.py` — 3 function signatures fixed
- `dreamtalk/face/core/animation/liveavatar/utils/model_manager.py` — 6 classes/methods fixed
- `dreamtalk/face/core/animation/liveavatar/utils/fp8_linear.py` — `FP8ScaleLinear.__init__`
- `dreamtalk/face/core/animation/liveavatar/utils/detectors/s3fd/__init__.py` — `S3FD.__init__`
- `dreamtalk/face/core/animation/liveavatar/utils/detectors/s3fd/nets.py` — `S3FDNet.__init__`
- `dreamtalk/face/core/lipsync/ditto/core/models/modules/LMDM.py` — constructor default
- `dreamtalk/face/core/animation/sadtalker/src/audio2pose_models/audio2pose.py` — constructor default
- `dreamtalk/face/core/animation/sadtalker/src/face3d/util/my_awing_arch.py` — `FAN.__init__`
- `dreamtalk/face/core/lipsync/musetalk/utils/face_detection/api.py` — `FaceAlignment.__init__`

### TTS Engine Adapters — Changed `device or 'cuda'` → `device or (auto-detect)`
- `dreamtalk/voice/core/tts/indic_tts_engine.py`
- `dreamtalk/voice/core/tts/svara_tts_engine.py`
- `dreamtalk/voice/core/tts/fastspeech2_hs_engine.py`
- `dreamtalk/voice/core/tts/indicf5_engine.py`

### Dockerfile
- **Already correct** — uses `nvidia/cuda:12.4.0-runtime-ubuntu22.04` base + CUDA torch

## 🔍 Items Verified Already Good (no changes needed)

Many items from the original audit already had proper fallback at the time of inspection:
- `croper.py:21` — has `device = 'cuda' if torch.cuda.is_available() else 'cpu'`
- `extract_kp_videos_safe.py:20,36` — both lines use conditional
- `discriminator.py:109,115` — both `.cuda()` calls guarded by `if torch.cuda.is_available()`
- `indic_tts/main.py:337-340` — guarded by `if use_cuda and torch.cuda.is_available()`
- `qsnn.py:83` (both copies) — guarded by `if torch.cuda.is_available()`
- `voice_pipeline.py:579+` — already uses `"cuda" if torch.cuda.is_available() else "cpu"`
- `avatar_server.py:500` — already uses GPU detection
- `feature_extract.py:46` — already uses conditional GPU selection

## 📋 Remaining Medium Items (not yet addressed)

| # | File | Issue |
|---|------|-------|
| 1 | `_check_deps.py:20-28` | Hardcoded `D:\\Anaconda\\...` torch path |
| 2 | MediaPipe | CPU-only — no GPU delegate configured |
| 3 | Training scripts (`train.py`, `run_demo.py`) | GPU required by design — CPU fallback not applicable |

## Already Good (25+ files with proper GPU fallback)

Files across `dreamtalk/voice/core/tts/`, `dreamtalk/face/core/lipsync/musetalk/`, `dreamtalk/face/core/animation/`, `dreamtalk/avatar/core/body/`, `dreamtalk/brain/`, `dreamtalk/cognition/` already use `torch.cuda.is_available()` for conditional GPU selection — verified on inspection.
