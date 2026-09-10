# Svara TTS API - Architecture Overview (adapted from Kenpath/svara-tts)

## System Architecture

The Svara TTS API runs as a **single process** with the vLLM inference engine embedded directly in the FastAPI application. This eliminates the HTTP hop between services, reducing latency and simplifying operations.

```
┌───────────────────────────────────────────────────────────┐
│                     Docker Container                       │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              Supervisord (Process Manager)           │  │
│  └───────────────────────┬─────────────────────────────┘  │
│                          │                                 │
│  ┌───────────────────────▼─────────────────────────────┐  │
│  │              FastAPI Server (Port 8080)              │  │
│  │                                                     │  │
│  │  ┌───────────────────────────────────────────────┐  │  │
│  │  │        Embedded vLLM Engine                   │  │  │
│  │  │        (AsyncLLMEngine singleton)             │  │  │
│  │  └───────────────────┬───────────────────────────┘  │  │
│  │                      │                              │  │
│  │  ┌───────────────────▼───────────────────────────┐  │  │
│  │  │           TTS Engine Components               │  │  │
│  │  │                                               │  │  │
│  │  │  ┌──────────────┐  ┌────────────┐  ┌───────┐ │  │  │
│  │  │  │ Orchestrator │  │   SNAC     │  │ Voice │ │  │  │
│  │  │  │              │  │  Decoder   │  │Config │ │  │  │
│  │  │  └──────────────┘  └────────────┘  └───────┘ │  │  │
│  │  │                                               │  │  │
│  │  └───────────────────────────────────────────────┘  │  │
│  │                                                     │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Supervisord (Process Manager)

**Purpose:** Manages the FastAPI process within the Docker container

**Features:**
- Automatic process restart on failure
- Log streaming to stdout/stderr
- Graceful shutdown handling

**Configuration:** [`supervisord.conf`](supervisord.conf)

### 2. Embedded vLLM Engine

**Purpose:** Runs the Svara TTS language model for token generation in-process

**Key Design:**
- **Singleton pattern**: `VLLMEmbeddedTransport` holds a class-level `AsyncLLMEngine` instance — GPU resources are allocated once at startup
- **`initialize_engine()`**: Called during FastAPI lifespan startup with env-var-driven configuration
- **Direct generation**: `engine.generate()` yields `RequestOutput` objects with accumulated text; the transport computes deltas
- **Request cancellation**: On error or client disconnect, `engine.abort(request_id)` frees vLLM resources

**Configuration (via environment variables):**

| Variable | Default | Description |
|----------|---------|-------------|
| `VLLM_MODEL` | `kenpath/svara-tts-v1` | Hugging Face model repository |
| `VLLM_GPU_MEMORY_UTILIZATION` | `0.9` | GPU memory usage (0.0-1.0) |
| `VLLM_MAX_MODEL_LEN` | `4096` | Maximum context length |
| `VLLM_TENSOR_PARALLEL_SIZE` | `1` | Number of GPUs for parallelism |
| `VLLM_DTYPE` | `auto` | Data type (`auto`, `float16`, `bfloat16`) |
| `VLLM_QUANTIZATION` | (none) | Quantization method (`fp8`, `awq`, `gptq`) |
| `VLLM_ENFORCE_EAGER` | `false` | Disable CUDA graphs (for debugging) |

### 3. FastAPI Server

**Purpose:** Public-facing REST API for text-to-speech synthesis

**Port:** 8080
**Framework:** FastAPI (async Python)

**Endpoints:**
- `GET /health` — Health check
- `GET /v1/voices` — List available voices
- `POST /v1/audio/speech` — OpenAI-compatible TTS (supports streaming, zero-shot cloning)

**Features:**
- Async/await for high concurrency
- Streaming audio response with format conversion
- Request validation with Pydantic
- Automatic API documentation (OpenAPI/Swagger at `/docs`)
- OpenAI SDK compatibility

### 4. TTS Engine Components

#### Orchestrator (`tts_engine/orchestrator.py`)

**Purpose:** Coordinates the TTS pipeline

**Flow:**
1. Accepts text and speaker_id
2. Encodes prompt via `svara_text_to_tokens()`
