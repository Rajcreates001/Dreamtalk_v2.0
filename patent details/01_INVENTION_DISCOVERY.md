# 01 — INVENTION DISCOVERY

## Date: August 21, 2026

---

## What DreamTalk Actually Does

DreamTalk is a production-grade Digital Twin Platform that creates autonomous AI virtual beings. The system:

1. Accepts user input (text, audio, image)
2. Processes input through a multi-stage pipeline
3. Detects emotion from both voice acoustics and text sentiment
4. Fuses emotion signals with confidence-weighted ensemble
5. Processes fused emotion through 5 simulated brain areas with SNN encoding
6. Selects an action type via basal ganglia neural competition
7. Generates a role-aware, emotion-modulated response via LLM
8. Produces synchronized multimodal output (avatar animation, cloned voice, persistent memory)

## What Was Built Specifically for DreamTalk

| Component | Built for DreamTalk? | Evidence |
|-----------|---------------------|----------|
| SNNEncoder (4 strategies) | YES — custom implementation | `pipeline/brain_pipeline.py:SNNEncoder` |
| PFCBrainArea (eligibility traces) | YES — custom implementation | `pipeline/brain_pipeline.py:PFCBrainArea` |
| dACCBrainArea (STDP learning) | YES — custom implementation | `pipeline/brain_pipeline.py:dACCBrainArea` |
| InsulaBrainArea (cognitive appraisal) | YES — custom implementation | `pipeline/brain_pipeline.py:InsulaBrainArea` |
| IPLBrainArea (multimodal integration) | YES — custom implementation | `pipeline/brain_pipeline.py:IPLBrainArea` |
| BasalGangliaBrainArea (action selection) | YES — custom implementation | `pipeline/brain_pipeline.py:BasalGangliaBrainArea` |
| WorkingMemory (decay/interference) | YES — custom implementation | `pipeline/brain_pipeline.py:WorkingMemory` |
| TextEmotionDetector (18-mood PAD) | YES — custom implementation | `pipeline/brain_pipeline.py:TextEmotionDetector` |
| EmotionFusion (dynamic weighting) | YES — custom implementation | `pipeline/voice_pipeline.py:fuse_emotion_profiles` |
| VoicePipeline (full analysis chain) | YES — custom orchestration | `pipeline/voice_pipeline.py` |
| FacePipeline (multi-backend) | YES — custom orchestration | `pipeline/face_pipeline.py` |
| PipelineOrchestrator (6-stage) | YES — custom implementation | `pipeline/orchestrator.py` |
| OrchestrationEngine (FSM) | YES — custom implementation | `orchestration/core/engine.py` |
| 7 Stage Handlers | YES — custom implementation | `orchestration/core/handlers.py` |
| CreationPipeline (11-step) | YES — custom implementation | `digital_twin/creation_pipeline.py` |
| PersonalityEngine | YES — custom implementation | `digital_twin/personality.py` |
| VRMViewer (3D avatar) | Partially — uses @pixiv/three-vrm | `frontend/src/components/vrm/vrm-viewer.tsx` |
| PADEmotionEngine (50+ states) | YES — custom implementation | `emotion/core/pad_model.py` |

## What Uses Known/Conventional Technology

| Component | Technology | Source |
|-----------|------------|--------|
| Face Detection | MediaPipe | Google (open source) |
| Face Detection Fallback | OpenCV DNN / Haar Cascade | OpenCV (open source) |
| Face Mesh | MediaPipe FaceMesh 478 landmarks | Google (open source) |
| 3D Face Model | FLAME | Published research (Li et al.) |
| ASR | Whisper | OpenAI (open source) |
| Sentiment Analysis | VADER | vaderSentiment (open source) |
| TTS | Kokoro, Edge-TTS, gTTS | Open source / Microsoft |
| Voice Conversion | RVC, IndicF5 | Open source |
| LLM Inference | OpenAI-compatible API | Various providers |
| 3D Rendering | Three.js + @pixiv/three-vrm | Open source |
| Frontend | Next.js 16 + React 19 | Open source |
| Backend | FastAPI + uvicorn | Open source |
| Database | PostgreSQL | Open source |
| ML Framework | PyTorch, NumPy, librosa | Open source |

## Invention Candidates (Ranked by Novelty Potential)

### 1. Neuromorphic SNN Brain Architecture (HIGH)
The 5-brain-area architecture with STDP learning, dopamine modulation, and basal ganglia action selection applied to conversational AI is the strongest invention candidate.

### 2. Multi-Modal Emotion Fusion (HIGH)
Dynamic confidence-weighted ensemble of voice acoustic and text sentiment emotion detection, with transparent provenance tracking.

### 3. Spike Train Text Encoding (MEDIUM-HIGH)
4-strategy spike encoding (rate, TTFS, phase, population) applied to NLP features for downstream SNN processing.

### 4. End-to-End Pipeline Orchestration (MEDIUM)
The specific 6-stage pipeline with cross-stage data flow (face → voice → emotion fusion → brain → animation → persistence).

### 5. Cascading Voice Cloning with Emotion Preservation (MEDIUM)
4-engine voice cloning cascade with emotion profile preservation and feedback into the fusion system.

### 6. Digital Twin Creation Pipeline (MEDIUM)
11-step automated creation with role-specific initialization and versioned evolution tracking.

---

*End of Invention Discovery*
