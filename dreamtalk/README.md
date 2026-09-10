# DreamTalk — AI Digital Twin Platform

A neuromorphic brain-inspired conversational AI platform with voice cloning, 3D avatar animation, and emotion-aware digital twins.

## Architecture

```
User Input (Text/Voice)
    → Brain Pipeline (SNN: PFC, dACC, Insula, IPL, BasalGanglia)
    → Emotion Detection (VADER + PAD model)
    → LLM Response (Ollama / OpenAI / fallback)
    → TTS Audio (Kokoro / IndicF5 / Edge-TTS)
    → Avatar Animation (Emotion → 30+ facial blendshapes)
    → Lip Sync (Phoneme → Viseme extraction)
    → Real-time WebSocket streaming
```

## Quick Start (Docker)

### Prerequisites
- Docker Desktop with GPU support
- NVIDIA GPU with 8GB+ VRAM
- 16GB+ system RAM
- ~20GB disk space for weights

### 1. Clone and Configure
```bash
cd dreamtalk
cp .env.example .env
# Edit .env with your settings
```

### 2. Start All Services
```bash
cd docker
docker compose -f docker-compose.dreamtalk.yml up -d
```

### 3. Verify Services
```bash
# Check all containers
docker ps -a --filter "name=dreamtalk"

# Check backend health
curl http://localhost:5001/health

# Check pipeline health
curl http://localhost:5001/pipeline/health

# Open frontend
# http://localhost:4000
```

### 4. Start Ollama (for brain LLM)
```bash
# On host machine:
ollama serve
ollama pull deepseek-r1:7b
```

## Services & Ports

| Service | Port | Description |
|---------|------|-------------|
| Backend (FastAPI) | 5001 | API server + WebSocket |
| Frontend (Next.js) | 4000 | Web UI |
| IndicF5 TTS | 8002 | Indian language TTS |
| PostgreSQL | 5433 | Database |
| Redis | 6380 | Cache + sessions |
| Weaviate | 8081 | Vector database |

## Features

### Brain Pipeline (Neuromorphic)
- **Prefrontal Cortex (PFC):** Executive function, response planning
- **dACC:** Conflict monitoring, intent validation
- **Insula:** Emotion processing, interoceptive awareness
- **IPL:** Context integration, multimodal binding
- **Basal Ganglia:** Action selection, response gating

### Voice
- **Kokoro TTS:** 54 voices, 9 languages (offline neural)
- **IndicF5:** 12 Indian languages (CPU inference)
- **Edge-TTS:** Multi-language Azure voices (online)
- **Voice Cloning:** Audio input → voice profile → custom TTS

### Avatar & Animation
- **LivePortrait:** Photo → talking head animation
- **MuseTalk:** Real-time lip sync from audio
- **Emotion Mapping:** PAD model → 30+ facial blendshapes
- **3D Avatars:** VRM/Three.js rendering

### Digital Twins
- Personalized AI assistants with persistent memory
- Personality profiles that evolve over time
- Knowledge base integration (Weaviate RAG)
- Multi-role support: personal, healthcare, business

## API Endpoints

### Authentication
- `POST /api/v1/auth/signup` — Create account
- `POST /api/v1/auth/login` — Login
- `POST /api/v1/auth/refresh` — Refresh token

### Chat
- `POST /api/chat/public` — Chat (no auth required)
- `POST /api/chat` — Chat (auth required)
- `WS /ws/chat` — WebSocket real-time chat

### Voice
- `POST /api/avatar/tts/generate` — Generate TTS audio
- `GET /api/avatar/tts/audio` — Get TTS audio file
- `POST /api/avatar/tts/indicf5` — IndicF5 TTS (Indian languages)
- `GET /api/avatar/tts/indicf5/languages` — List IndicF5 languages

### Digital Twins
- `GET /api/v1/digital-twins` — List twins
- `POST /api/v1/digital-twins` — Create twin
- `GET /api/v1/digital-twins/{id}` — Get twin
- `PUT /api/v1/digital-twins/{id}` — Update twin
- `DELETE /api/v1/digital-twins/{id}` — Delete twin

### Avatar
- `POST /api/avatar/video/generate` — Generate avatar video
- `POST /api/avatar/video/liveportrait/generate` — LivePortrait animation
- `POST /api/avatar/face/generate-mesh` — Generate face mesh
- `GET /api/avatar/status` — Avatar system status

### Pipeline
- `GET /pipeline/health` — Pipeline component health
- `GET /analytics/emotions` — Emotion analytics
- `GET /analytics/brain` — Brain activity data

## Development

### Local Development (without Docker)
```bash
# Install dependencies
pip install -r requirements-full.txt

# Start PostgreSQL, Redis, Weaviate
# (use Docker for just these)
cd docker
docker compose up -d postgres redis weaviate

# Run backend
cd ..
PYTHONPATH=. uvicorn dreamtalk.backend.main:app --reload --port 5001

# Run frontend
cd frontend
npm install
npm run dev
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

### Running Tests
```bash
# Backend tests
cd dreamtalk
python -m pytest tests/ -v

# E2E API tests
python tests/test_e2e_api.py

# Frontend tests
cd frontend
npm test
```

## Project Structure

```
dreamtalk/
├── backend/              # FastAPI backend
│   ├── api/v1/          # API endpoints (auth, digital-twins, avatar, chat)
│   ├── middleware/       # Rate limiter, input validation
│   ├── services/        # Voice orchestrator, business logic
│   ├── websocket/       # WebSocket chat handler
│   └── main.py          # FastAPI app entry point
├── pipeline/             # Core AI pipeline
│   ├── brain_pipeline.py    # SNN neuromorphic brain
│   ├── emotion_animation.py # Emotion → facial expression
│   ├── lipsync_pipeline.py  # Audio → lip sync
│   ├── orchestrator.py      # Full pipeline orchestration
│   ├── session_manager.py   # Session persistence
│   ├── model_manager.py     # Model lazy loading
│   ├── resilience.py        # Circuit breaker, retry
│   ├── health.py            # Pipeline health monitor
│   └── analytics.py         # Emotion/brain analytics
├── voice/                # Voice processing modules
│   ├── core/tts/        # TTS engines (Kokoro, IndicF5, Edge-TTS)
│   └── core/vc/         # Voice cloning, IndicF5 microservice
├── brain/                # Brain modules
│   ├── llm/             # LLM integration (Ollama, OpenAI)
│   └── emotion/         # Emotion detection (VADER, PAD)
├── frontend/             # Next.js 16 frontend
│   ├── src/app/         # Pages (43 routes)
│   ├── src/components/  # React components (192)
│   └── src/hooks/       # Custom hooks (useWebSocket, useChat)
├── docker/               # Docker configuration
│   ├── Dockerfile       # Backend image
│   ├── Dockerfile.frontend  # Frontend image
│   ├── Dockerfile.indicf5   # IndicF5 image
│   └── docker-compose.dreamtalk.yml  # Full stack compose
├── weights/              # Model weights (14GB)
├── scripts/              # Utility scripts
├── patent details/       # Patent documentation
└── E2E_TEST_REPORT.md   # Test results
```

## Environment Variables

See `.env.example` for all configuration options. Key variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | PostgreSQL host | `localhost` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/1` |
| `JWT_SECRET` | JWT signing key | **Must change in production** |
| `GPU_SERVER_BASE_URL` | Ollama/LLM URL | `http://localhost:11434/v1` |
| `LLM_MODEL_NAME` | LLM model to use | `deepseek-r1:7b` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:4000` |

## Troubleshooting

### Backend won't start
```bash
docker logs dreamtalk-backend --tail 50
```

### TTS not working
```bash
# Check Kokoro voices
curl http://localhost:5001/api/avatar/status

# Check IndicF5
curl http://localhost:8002/health
```

### Brain LLM unreachable
```bash
# Start Ollama on host
ollama serve
ollama pull deepseek-r1:7b

# Verify from Docker
docker exec dreamtalk-backend curl -s http://host.docker.internal:11434/api/tags
```

### GPU out of memory
```bash
# Check GPU usage
nvidia-smi

# Reduce model size or use CPU
export CUDA_VISIBLE_DEVICES=""
```

## License

Private — All rights reserved.

---

Built with ❤️ by the DreamTalk team.
