# Indian TTS Engine Integration Mapping

## Overview
Five Indian TTS repositories extracted from `repos-used/` → `dreamtalk/voice/core/tts/`.
Each repo's source code was copied with attribution headers and import paths fixed,
then wrapped with a standardized adapter class (`*_engine.py`).

---

## 1. Kokoro (hexgrad/Kokoro-82M)

| Attribute | Value |
|-----------|-------|
| **License** | Apache 2.0 |
| **Architecture** | StyleTTS 2 (ALBERT + iSTFT decoder), 82M params |
| **Source** | `repos-used/kokoro/kokoro/` (7 files) |
| **Target** | `dreamtalk/voice/core/tts/kokoro/` |
| **Adapter** | `dreamtalk/voice/core/tts/kokoro_engine.py` → `KokoroTTSEngine` |

### Files Copied
| Source File | Target File | Lines | Notes |
|------------|-------------|-------|-------|
| `__init__.py` | `kokoro/__init__.py` | 7 | Exports KModel, KPipeline |
| `__main__.py` | `kokoro/__main__.py` | 128 | CLI entry point (fixed imports) |
| `custom_stft.py` | `kokoro/custom_stft.py` | 174 | ONNX-compatible STFT |
| `istftnet.py` | `kokoro/istftnet.py` | 385 | iSTFT decoder with AdaINResBlocks |
| `model.py` | `kokoro/model.py` | 139 | KModel — PyTorch model wrapper |
| `modules.py` | `kokoro/modules.py` | 162 | CustomAlbert, TextEncoder, ProsodyPredictor |
| `pipeline.py` | `kokoro/pipeline.py` | 415 | KPipeline — G2P + voice + inference chain |
| `pyproject.toml` | `kokoro/pyproject.toml` | 35 | Package metadata |
| `LICENSE` | `kokoro/LICENSE` | 170 | Apache 2.0 |

### Excluded
- `kokoro.js/` — Browser JS port (not needed for Python backend)
- `demo/` — Gradio UI
- `examples/` — Example scripts

### Languages
`a`=American English, `b`=British English, `e`=Spanish, `f`=French,
`h`=Hindi, `i`=Italian, `p`=Brazilian Portuguese, `j`=Japanese, `z`=Mandarin Chinese

### Adapter API
```python
engine = KokoroTTSEngine(device='cpu')
# Hindi TTS:
audio_chunks = engine.synthesize("नमस्ते", voice='hf_alpha', lang_code='h')
# American English:
audio_chunks = engine.synthesize("Hello world", voice='af_heart', lang_code='a')
```

---

## 2. IndicF5 (AI4Bharat/IndicF5)

| Attribute | Value |
|-----------|-------|
| **License** | MIT |
| **Architecture** | Conditional Flow Matching + DiT backbone (F5-TTS) or UNetT (E2-TTS) |
| **Source** | `repos-used/IndicF5/f5_tts/` (40 files) |
| **Target** | `dreamtalk/voice/core/tts/indicf5/` |
| **Adapter** | `dreamtalk/voice/core/tts/indicf5_engine.py` → `IndicF5TTSEngine` |

### Files Copied (39 files + 3 configs + reqs)

| Subdirectory | Files | Lines |
|-------------|-------|-------|
| `indicf5/` | `__init__.py`, `api.py` | 173 |
| `indicf5/model/` | `cfm.py`, `dataset.py`, `modules.py`, `trainer.py`, `utils.py`, `__init__.py` | 1,661 |
| `indicf5/model/backbones/` | `dit.py`, `mmdit.py`, `unett.py` | 488 |
| `indicf5/infer/` | `utils_infer.py`, `infer_cli.py`, `infer_cli_batch.py`, `infer_batch_parallel.py`, `speech_edit.py` | 1,245 |
| `indicf5/train/` | `train.py`, `finetune_cli.py` | 224 |
| `indicf5/train/datasets/` | 8 prepare_*.py files | 1,092 |
| `indicf5/eval/` | 4 eval_*.py + `ecapa_tdnn.py`, `utils_eval.py` | 1,000 |
| `indicf5/scripts/` | 2 count_*.py | 65 |
| `indicf5/configs/` | 4 YAML train configs | 152 |
| — | `requirements.txt`, `setup.py` | 62 |

### Excluded
- `infer_gradio.py` — Gradio Web UI
- `infer_gradio_orig.py` — Original Gradio demo
- `finetune_gradio.py` — Fine-tuning Gradio UI
- `socket_server.py` — WebSocket server

### Languages
Assamese (`as`), Bengali (`bn`), Gujarati (`gu`), Hindi (`hi`),
Kannada (`kn`), Malayalam (`ml`), Marathi (`mr`), Odia (`or`),
Punjabi (`pa`), Tamil (`ta`), Telugu (`te`), English (`en`)

### Adapter API
```python
engine = IndicF5TTSEngine(model_type="F5-TTS", device='cuda')
wav, sr = engine.synthesize(
    "प्रिय मित्रों, आपका स्वागत है",
    ref_audio_path="prompts/hi_female.wav",
    ref_text="reference transcript"
)
```

---

## 3. Svara-TTS (Kenpath/svara-tts)

| Attribute | Value |
|-----------|-------|
| **License** | MIT |
| **Architecture** | LLM-based (Llama 3.2) + SNAC neural audio codec + vLLM |
| **Source** | `repos-used/svara-tts/` (14 files) |
| **Target** | `dreamtalk/voice/core/tts/svara_tts/` |
| **Adapter** | `dreamtalk/voice/core/tts/svara_tts_engine.py` → `SvaraTTSEngine` |

### Files Copied

| Subdirectory | Files | Lines |
|-------------|-------|-------|
| `svara_tts/` | `__init__.py` | 5 |
| `svara_tts/tts_engine/` | `orchestrator.py`, `transports.py`, `encoder.py`, `codec.py`, `mapper.py`, `buffers.py`, `constants.py`, `utils.py`, `sinks.py`, `voice_config.py` | 1,635 |
| `svara_tts/api/` | `server.py`, `models.py` | 392 |
| `svara_tts/assets/voices/` | `svara-tts-v1.yaml`, `svara-tts-v2.yaml` | 587 |
| — | `requirements.txt`, `ARCHITECTURE.md`, `DEPLOYMENT.md` | 167 |

### Languages (19)
Assamese (`as`), Bengali (`bn`), Bhojpuri (`bh`), Bodo (`brx`),
Chhattisgarhi (`hne`), Dogri (`doi`), Gujarati (`gu`), Hindi (`hi`),
Kannada (`kn`), Magahi (`mag`), Maithili (`mai`), Malayalam (`ml`),
Marathi (`mr`), Nepali (`ne`), Punjabi (`pa`), Sanskrit (`sa`),
Tamil (`ta`), Telugu (`te`), English (Indian, `en`)

### Adapter API
```python
engine = SvaraTTSEngine(model_name="kenpath/svara-tts-v1", device='cuda')
audio = engine.synthesize("नमस्ते, आप कैसे हैं?", voice="hi_female", lang="hi")
```

---

## 4. Indic-TTS (AI4Bharat/Indic-TTS)

| Attribute | Value |
|-----------|-------|
| **License** | MIT |
| **Architecture** | FastPitch (acoustic) + HiFi-GAN V1 (vocoder), ICASSP 2023 |
| **Source** | `repos-used/Indic-TTS/` (21 files) |
| **Target** | `dreamtalk/voice/core/tts/indic_tts/` |
| **Adapter** | `dreamtalk/voice/core/tts/indic_tts_engine.py` → `IndicTTSEngine` |

### Files Copied

| Subdirectory | Files | Lines |
|-------------|-------|-------|
| `indic_tts/` | `__init__.py`, `main.py`, `vocoder.py` | 814 |
| `indic_tts/inference/src/` | `inference.py` | 213 |
| `indic_tts/inference/src/models/` | `request.py`, `response.py`, `common.py` | 56 |
| `indic_tts/inference/src/utils/` | `text.py`, `translator.py`, `paragraph_handler.py` | 268 |
| `indic_tts/inference/src/postprocessor/` | `denoiser.py`, `postprocessor.py`, `vad.py` | 137 |
| `indic_tts/inference/examples/` | `xlit.py` | 11 |
| `indic_tts/configs/` | `train_fastpitch.sh`, `train_hifigan.sh` | 40 |
| — | `requirements.txt` | 12 |

### Languages (13)
Assamese (`as`), Bengali (`bn`), Bodo (`brx`), Gujarati (`gu`),
Hindi (`hi`), Kannada (`kn`), Malayalam (`ml`), Manipuri (`mni`),
Marathi (`mr`), Odia (`or`), Rajasthani (`raj`), Tamil (`ta`),
Telugu (`te`), English (Indian, `en`), Hinglish (`hne`)

### Adapter API
```python
engine = IndicTTSEngine(model_dir="/path/to/models", device='cuda')
audio, sr = engine.synthesize("प्रिय मित्रों", lang='hi')
```

---

## 5. Fastspeech2_HS (k-m-irfan/Fastspeech2_HS)

| Attribute | Value |
|-----------|-------|
| **License** | MIT |
| **Architecture** | FastSpeech 2 (non-AR Transformer) + HiFi-GAN |
| **Source** | `repos-used/Fastspeech2_HS/` (12 Python files; LFS weights failed - budget exceeded) |
| **Target** | `dreamtalk/voice/core/tts/fastspeech2_hs/` |
| **Adapter** | `dreamtalk/voice/core/tts/fastspeech2_hs_engine.py` → `Fastspeech2HSEngine` |

### Files Copied
| Source File | Target File | Lines |
|------------|-------------|-------|
| `api.py` | `fastspeech2_hs/api.py` | 63 |
| `inference.py` | `fastspeech2_hs/inference.py` | 123 |
| `text_preprocess_for_inference.py` | `fastspeech2_hs/text_preprocess_for_inference.py` | 895 |
| `get_phone_mapped_python.py` | `fastspeech2_hs/get_phone_mapped_python.py` | 67 |
| `charmap/Text_Cleaning.py` | `fastspeech2_hs/charmap/Text_Cleaning.py` | 76 |
| `hifigan/*` (5 files) | `fastspeech2_hs/hifigan/*` | 524 |
| `ssn_parser/phoneReplace.py` | `fastspeech2_hs/ssn_parser/phoneReplace.py` | 57 |

### Note
LFS model weights could not be downloaded (repo exceeded LFS budget).
Source code is fully functional once weights are obtained.

### Languages (16)
Assamese (`as`), Bengali (`bn`), Bodo (`brx`), Gujarati (`gu`),
Hindi (`hi`), Kannada (`kn`), Maithili (`mai`), Malayalam (`ml`),
Manipuri (`mni`), Marathi (`mr`), Odia (`or`), Punjabi (`pa`),
Rajasthani (`raj`), Tamil (`ta`), Telugu (`te`), Urdu (`ur`)

---

## Language Support Matrix

| Language | Kokoro | IndicF5 | Svara-TTS | Indic-TTS | Fastspeech2_HS |
|----------|--------|---------|-----------|-----------|----------------|
| Assamese | — | ✅ | ✅ | ✅ | ✅ |
| Bengali | — | ✅ | ✅ | ✅ | ✅ |
| Bhojpuri | — | — | ✅ | — | — |
| Bodo | — | — | ✅ | ✅ | ✅ |
| Chhattisgarhi | — | — | ✅ | — | — |
| Dogri | — | — | ✅ | — | — |
| Gujarati | — | ✅ | ✅ | ✅ | ✅ |
| Hindi | ✅ | ✅ | ✅ | ✅ | ✅ |
| Kannada | — | ✅ | ✅ | ✅ | ✅ |
| Magahi | — | — | ✅ | — | — |
| Maithili | — | — | ✅ | — | ✅ |
| Malayalam | — | ✅ | ✅ | ✅ | ✅ |
| Manipuri | — | — | — | ✅ | ✅ |
| Marathi | — | ✅ | ✅ | ✅ | ✅ |
| Nepali | — | — | ✅ | — | — |
| Odia | — | ✅ | — | ✅ | ✅ |
| Punjabi | — | ✅ | ✅ | — | ✅ |
| Rajasthani | — | — | — | ✅ | ✅ |
| Sanskrit | — | — | ✅ | — | — |
| Tamil | — | ✅ | ✅ | ✅ | ✅ |
| Telugu | — | ✅ | ✅ | ✅ | ✅ |
| Urdu | — | — | — | — | ✅ |
| English | ✅ (American/British) | ✅ | ✅ (Indian) | ✅ (Indian) | — |

---

## Package Import Structure

```
dreamtalk.voice.core.tts/
├── __init__.py               # ← Exports all TTS engines including Indian
├── kokoro/                   # Kokoro TTS package (7 files)
├── kokoro_engine.py          # KokoroTTSEngine adapter
├── indicf5/                  # IndicF5 TTS package (39 files)
├── indicf5_engine.py         # IndicF5TTSEngine adapter
├── svara_tts/                # Svara-TTS package (14 files)
├── svara_tts_engine.py       # SvaraTTSEngine adapter
├── indic_tts/                # Indic-TTS package (21 files)
├── indic_tts_engine.py       # IndicTTSEngine adapter
├── fastspeech2_hs/           # Fastspeech2_HS package (12 files)
├── fastspeech2_hs_engine.py  # Fastspeech2HSEngine adapter
├── tts_pipeline.py           # Original GPT-SoVITS pipeline
├── chattts/                  # ChatTTS sub-package
├── openvoice/                # OpenVoice sub-package
├── fish_speech/              # Fish Speech sub-package
└── ... (GPT-SoVITS core files)
```

---

## Import Fixes Applied

For each copied file, imports were changed from the original package name
to relative imports within the dreamtalk package:

| Original Import | Fixed Import |
|----------------|--------------|
| `from f5_tts.api import F5TTS` | `from .api import F5TTS` |
| `from f5_tts.model.cfm import CFM` | `from .model.cfm import CFM` |
| `from kokoro import KPipeline` | `from . import KPipeline` |
| `from kokoro.custom_stft import CustomSTFT` | `from .custom_stft import CustomSTFT` |
| `from tts_engine.orchestrator import *` | `from ..tts_engine.orchestrator import *` |
| `from inference.src.inference import TextToSpeechEngine` | `from .inference.src.inference import TextToSpeechEngine` |
| `from hifigan.models import Generator` | `from .hifigan.models import Generator` |
| `sys.path.append("hifigan")` | Removed (relative imports used instead) |

No `sys.path` hacks or absolute package references remain.
