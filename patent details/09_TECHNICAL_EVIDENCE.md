# 09 — TECHNICAL EVIDENCE

## Date: August 21, 2026

---

## Evidence Inventory

### Candidate 1: Neuromorphic SNN Brain Architecture

| Evidence Type | Location | Details | Strength |
|--------------|----------|---------|----------|
| Source code | `pipeline/brain_pipeline.py` | 1260 lines, 5 brain area classes fully implemented | HIGH |
| SNNEncoder | `pipeline/brain_pipeline.py:SNNEncoder` | 4 encoding strategies (rate, TTFS, phase, population), ~100 lines | HIGH |
| PFCBrainArea | `pipeline/brain_pipeline.py:PFCBrainArea` | Eligibility trace, dopamine modulation, working memory integration | HIGH |
| dACCBrainArea | `pipeline/brain_pipeline.py:dACCBrainArea` | STDP learning, entropy-based conflict monitoring | HIGH |
| InsulaBrainArea | `pipeline/brain_pipeline.py:InsulaBrainArea` | Cognitive appraisal map, homeostasis drift, emotional valence | HIGH |
| IPLBrainArea | `pipeline/brain_pipeline.py:IPLBrainArea` | Cross-modal weight matrices, integration ratio | HIGH |
| BasalGangliaBrainArea | `pipeline/brain_pipeline.py:BasalGangliaBrainArea` | D1/D2 pathways, 12 action types, softmax, TD learning | HIGH |
| WorkingMemory | `pipeline/brain_pipeline.py:WorkingMemory` | Capacity-7, decay, interference, attention focus | HIGH |
| Integration | `pipeline/brain_pipeline.py:BrainPipeline.make_decision()` | Full pipeline: encode → PFC → dACC → Insula → IPL → BG → LLM | HIGH |
| Tests | `tests/test_brain.py`, `tests/test_brain2.py`, `tests/test_brain_v2.py` | Test files exist (content not verified) | MEDIUM |

### Candidate 2: Multi-Modal Emotion Fusion

| Evidence Type | Location | Details | Strength |
|--------------|----------|---------|----------|
| Voice emotion | `pipeline/voice_pipeline.py:predict_emotion_from_voice()` | 7 acoustic features → 7 emotions → PAD | HIGH |
| Text emotion | `pipeline/brain_pipeline.py:TextEmotionDetector` | VADER + 10 keyword dictionaries → 18 moods → PAD | HIGH |
| Fusion | `pipeline/voice_pipeline.py:fuse_emotion_profiles()` | Dynamic weighting, provenance tracking | HIGH |
| Integration | `pipeline/orchestrator.py` Step 3 | Emotion fusion wired into pipeline | HIGH |
| PAD mapping | `pipeline/brain_pipeline.py:PAD_MOOD_MAP` | 18 mood states → PAD coordinates + activation | HIGH |
| EMA smoothing | `pipeline/brain_pipeline.py:TextEmotionDetector.analyze()` | α=0.35 exponential moving average for valence | MEDIUM |

### Candidate 3: End-to-End Pipeline

| Evidence Type | Location | Details | Strength |
|--------------|----------|---------|----------|
| Orchestrator | `pipeline/orchestrator.py` | 6-stage pipeline with step tracking | HIGH |
| Models | `pipeline/models.py` | Pydantic models for all pipeline results | HIGH |
| DB persistence | `pipeline/orchestrator.py` Step 7 | Pipeline results stored in PostgreSQL | HIGH |
| Media storage | `pipeline/orchestrator.py` Steps 1-2 | Assets stored in MediaRepository | MEDIUM |

### Candidate 4: Voice Cloning Cascade

| Evidence Type | Location | Details | Strength |
|--------------|----------|---------|----------|
| IndicF5 | `voice/core/vc/indicf5_converter.py` | CFM-based cloning, 1.34GB model | HIGH |
| RVC | `voice/core/vc/rvc/` | Retrieval-based conversion, 4 pretrained models | HIGH |
| OpenVoice | `voice/core/tts/openvoice/` | Tone color cloning | MEDIUM |
| Cascade logic | `pipeline/voice_pipeline.py:clone_voice()` | 4-engine priority cascade | HIGH |
| TTS engines | `voice/core/tts/MAPPING.md` | 5 TTS engines mapped | HIGH |
| Multi-language | `voice/core/tts/MAPPING.md` | 22+ languages across 5 engines | HIGH |

### Candidate 5: Digital Twin Creation

| Evidence Type | Location | Details | Strength |
|--------------|----------|---------|----------|
| Pipeline | `digital_twin/creation_pipeline.py` | 11-step creation | HIGH |
| DB schema | `backend/db/schema.sql` | 32+ tables, digital_twins table | HIGH |
| Personality | `digital_twin/personality.py` | Big Five + communication style | MEDIUM |
| Learning | `digital_twin/learning.py`, `digital_twin/learning_orchestrator.py` | Learning observation system | MEDIUM |
| Identity | `identity/models.py`, `identity/engine.py` | Identity profile system | MEDIUM |

### Candidate 6: Frontend 3D Avatar

| Evidence Type | Location | Details | Strength |
|--------------|----------|---------|----------|
| VRM viewer | `frontend/src/components/vrm/vrm-viewer.tsx` | Three.js + @pixiv/three-vrm | MEDIUM |
| Expression | `frontend/src/components/vrm/vrm-expression.tsx` | Expression controls | MEDIUM |
| Lip sync | `frontend/src/components/vrm/vrm-lipsync.tsx` | Lip sync component | MEDIUM |
| Cursor tracker | `frontend/src/components/vrm/vrm-cursor-tracker.tsx` | Gaze tracking | LOW |

---

## Experimental Evidence Status

| Experiment | Status | Location | Notes |
|------------|--------|----------|-------|
| End-to-end latency | NOT MEASURED | — | Need timing instrumentation |
| Emotion fusion accuracy | NOT MEASURED | — | Need ground truth dataset |
| SNN brain correlation | NOT MEASURED | — | Need activation vs quality analysis |
| Avatar sync accuracy | NOT MEASURED | — | Need frame-level analysis |
| Voice cloning MOS | NOT MEASURED | — | Need listening tests |
| Baseline comparison | NOT MEASURED | — | Need without-SNN control |

---

## Code Quality Evidence

| Metric | Value | Location |
|--------|-------|----------|
| Python files | ~3,324 | Project root |
| TypeScript/TSX files | ~261 | `frontend/src/` |
| Database tables | 32+ | `backend/db/schema.sql` |
| API endpoints | 93+ | `backend/api/v1/endpoints/` |
| Brain pipeline lines | 1,260 | `pipeline/brain_pipeline.py` |
| Voice pipeline lines | 1,429 | `pipeline/voice_pipeline.py` |
| Face pipeline lines | ~800 | `pipeline/face_pipeline.py` |
| Orchestrator lines | ~280 | `pipeline/orchestrator.py` |

---

*End of Technical Evidence*
