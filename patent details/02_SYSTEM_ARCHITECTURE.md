# 02 — SYSTEM ARCHITECTURE

## Date: August 21, 2026

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                               │
│  Next.js 16 Frontend (React 19, Three.js, @pixiv/three-vrm) │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Chat UI  │ │ Avatar   │ │ Dashboard│ │ Login/   │       │
│  │          │ │ 3D VRM   │ │          │ │ Signup   │       │
│  └────┬─────┘ └────┬─────┘ └──────────┘ └──────────┘       │
│       │ WebSocket + HTTP                                      │
└───────┼──────────────────────────────────────────────────────┘
        │
┌───────┼──────────────────────────────────────────────────────┐
│       ▼            SERVER LAYER                               │
│  FastAPI Backend (port 5001)                                  │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ 14 API Routers: auth, chat, avatar, voice, pipeline, │    │
│  │ digital_humans, digital_twins, identity, profile,     │    │
│  │ workforce, tasks, emotion, cognition                  │    │
│  └──────────────────────┬───────────────────────────────┘    │
│                         │                                     │
│  ┌──────────────────────▼───────────────────────────────┐    │
│  │           PIPELINE ORCHESTRATION LAYER                 │    │
│  │                                                        │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐                │    │
│  │  │  Face   │ │  Voice  │ │  Brain  │                │    │
│  │  │Pipeline │ │Pipeline │ │Pipeline │                │    │
│  │  └────┬────┘ └────┬────┘ └────┬────┘                │    │
│  │       │           │           │                        │    │
│  │       └─────┬─────┘           │                        │    │
│  │             │                 │                        │    │
│  │       ┌─────▼─────┐          │                        │    │
│  │       │  Emotion  │◄─────────┘                        │    │
│  │       │  Fusion   │                                   │    │
│  │       └─────┬─────┘                                   │    │
│  │             │                                          │    │
│  │       ┌─────▼─────────────────────────────┐           │    │
│  │       │     NEUROMORPHIC BRAIN            │           │    │
│  │       │  SNN Encoder → PFC → dACC →       │           │    │
│  │       │  Insula → IPL → Basal Ganglia     │           │    │
│  │       │  → LLM Response                   │           │    │
│  │       └─────┬─────────────────────────────┘           │    │
│  │             │                                          │    │
│  │       ┌─────▼─────────┐  ┌──────────┐                │    │
│  │       │  Animation    │  │  Persist │                │    │
│  │       │  (LivePortrait│  │  (DB +   │                │    │
│  │       │   /FLAME)     │  │  Media)  │                │    │
│  │       └───────────────┘  └──────────┘                │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │           SERVICE LAYER                               │    │
│  │  LLM Service │ Knowledge Base │ Redis Cache │         │    │
│  │  Weaviate    │ Celery Tasks   │ Sentry      │         │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │           DATA LAYER                                  │    │
│  │  PostgreSQL (32+ tables) │ Media Repository │         │    │
│  │  Pipeline Outputs        │ Voice Assets     │         │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## Component Interaction Map

### SNN Brain Area Interconnections

```
                    Text Input
                        │
                        ▼
                 ┌──────────────┐
                 │  SNNEncoder  │
                 │ (rate/ttfs/  │
                 │  phase/pop)  │
                 └──────┬───────┘
                        │ spike train
                        ▼
                 ┌──────────────┐
        ┌──────►│     PFC      │◄──── Eligibility Trace
        │       │  (Planning)  │◄──── Dopamine Signal
        │       └──────┬───────┘
        │              │ pfc_output
        │       ┌──────▼───────┐
        │       │    dACC      │◄──── STDP Learning
        │       │  (Conflict)  │
        │       └──────┬───────┘
        │              │ conflict_score
        │              │
        │       ┌──────▼───────┐    ┌──────────────┐
        │       │     IPL      │◄───│  Audio Input │
        │       │ (Integration)│    └──────────────┘
        │       └──────┬───────┘
        │              │ integrated_features
        │              │
        │       ┌──────▼───────┐    ┌──────────────┐
        │       │    Insula    │◄───│   Emotion    │
        │       │ (Emotion)    │    │   Features   │
        │       └──────┬───────┘    └──────────────┘
        │              │ insula_valence
        │              │
        │       ┌──────▼───────────────────────┐
        │       │      Basal Ganglia            │
        │       │  (Action Selection)           │
        │       │  D1 Pathway ←──(1-conflict)──┤
        │       │  D2 Pathway ←──(conflict)────┤
        │       │  Softmax + Exploration        │
        │       └──────┬───────────────────────┘
        │              │ selected_action (1 of 12)
        │              │
        │       ┌──────▼───────┐
        └──────►│     LLM      │
                │  (Response)  │
                └──────┬───────┘
                       │ response_text
                       ▼
                BrainDecisionResult
```

### Emotion Fusion Architecture

```
    Voice Input                    Text Input
         │                              │
         ▼                              ▼
┌─────────────────┐          ┌─────────────────┐
│ Acoustic Feature │          │ VADER Sentiment  │
│ Extraction       │          │ + Keyword Match  │
│ (7 categories)   │          │ (18 moods)       │
└────────┬────────┘          └────────┬────────┘
         │                            │
         ▼                            ▼
┌─────────────────┐          ┌─────────────────┐
│ Voice Emotion    │          │ Text Emotion     │
│ Prediction       │          │ Detection        │
│ (7 emotions)     │          │ (PAD mapping)    │
└────────┬────────┘          └────────┬────────┘
         │                            │
         │ voice_confidence           │ text_confidence
         │                            │
         ▼                            ▼
    ┌────────────────────────────────────┐
    │     Dynamic Ensemble Weighting      │
    │  vw = min(vc * 0.4 + 0.1, 0.6)    │
    │  tw = min(tc * 0.4 + 0.1, 0.6)    │
    │  vw = vw / (vw + tw)               │
    │  tw = tw / (vw + tw)               │
    └───────────────┬────────────────────┘
                    │
                    ▼
         ┌──────────────────┐
         │  Fused PAD       │
         │  Valence, Arousal│
         │  + Provenance    │
         └──────────────────┘
```

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Frontend | Next.js | 16.2.9 |
| Frontend UI | React | 19.2.4 |
| 3D Rendering | Three.js | 0.183.0 |
| Avatar Model | @pixiv/three-vrm | 3.5.4 |
| Animation | Motion (Framer) | 12.40.0 |
| Backend Framework | FastAPI | ≥0.115.0 |
| ASGI Server | Uvicorn | ≥0.34.0 |
| Database | PostgreSQL | 15+ |
| DB Driver | asyncpg | ≥0.30.0 |
| ML Framework | PyTorch | (via dt_venv) |
| Audio Processing | librosa | ≥0.10.0 |
| Face Detection | MediaPipe | ≥0.10.0 |
| Sentiment | VADER | (via vaderSentiment) |
| TTS | Kokoro, Edge-TTS, gTTS | various |
| Voice Conversion | RVC, IndicF5 | various |
| Vector DB | Weaviate | ≥4.0.0 |
| Cache | Redis | ≥5.0.0 |
| Task Queue | Celery | ≥5.3.0 |
| Error Tracking | Sentry | (optional) |

---

*End of System Architecture*
