# syntax=docker/dockerfile:1
# ═══════════════════════════════════════════════════════════════════════
# DreamTalk Backend — Optimized Multi-Stage Dockerfile
#
# Features:
#   ✅ Multi-stage build (deps → pydeps → runtime)
#   ✅ BuildKit pip cache mounts for ~2× faster rebuilds
#   ✅ Split requirements layers (torch → core → ml → face → voice → brain)
#   ✅ Slim runtime stage — no build tools, no PPA
#   ✅ GPU device detection built-in via dreamtalk/shared/utils/device.py
# ═══════════════════════════════════════════════════════════════════════

# ─── Build args ─────────────────────────────────────────────────────
ARG CUDA_VERSION=12.4.0
ARG UBUNTU_VERSION=ubuntu22.04
ARG TORCH_VERSION=2.5.1
ARG TORCHVISION_VERSION=0.20.1
ARG TORCHAUDIO_VERSION=2.5.1
ARG TORCH_CUDA=cu124
ARG PYTHON_VERSION=3.11
ARG MAX_JOBS=4

# ====================================================================
# STAGE 1: System Dependencies (Python + build tools)
# ====================================================================
FROM nvidia/cuda:${CUDA_VERSION}-runtime-${UBUNTU_VERSION} AS deps

ARG PYTHON_VERSION
ARG MAX_JOBS

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TF_ENABLE_ONEDNN_OPTS=0 \
    KMP_DUPLICATE_LIB_OK=TRUE \
    DEBIAN_FRONTEND=noninteractive \
    MAX_JOBS=${MAX_JOBS}

# Install system deps + Python 3.11 from deadsnakes PPA
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y --no-install-recommends \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-dev \
    python${PYTHON_VERSION}-distutils \
    python${PYTHON_VERSION}-venv \
    ffmpeg \
    libgl1 \
    libegl1 \
    libgles2 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up python3 → python3.11 symlinks
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python${PYTHON_VERSION} 1

# Upgrade pip
RUN python${PYTHON_VERSION} -m ensurepip --upgrade && \
    python${PYTHON_VERSION} -m pip install --upgrade pip setuptools wheel

# Create output directories
RUN mkdir -p /app/pipeline_outputs/tts

# ====================================================================
# STAGE 2: Python Dependencies (layer-cached via BuildKit)
# ====================================================================
FROM deps AS pydeps

ARG TORCH_VERSION
ARG TORCHVISION_VERSION
ARG TORCHAUDIO_VERSION
ARG TORCH_CUDA

# ── Layer 1: PyTorch + CUDA (largest; cuDNN is in the base image) ──
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install \
    "torch==${TORCH_VERSION}+${TORCH_CUDA}" \
    "torchvision==${TORCHVISION_VERSION}+${TORCH_CUDA}" \
    "torchaudio==${TORCHAUDIO_VERSION}+${TORCH_CUDA}" \
    --index-url "https://download.pytorch.org/whl/${TORCH_CUDA}"

# ── Layer 2: Core backend ───────────────────────────────────────────
COPY requirements-core.txt /tmp/requirements-core.txt
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install -r /tmp/requirements-core.txt

# ── Layer 3: ML frameworks ──────────────────────────────────────────
COPY requirements-ml.txt /tmp/requirements-ml.txt
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install -r /tmp/requirements-ml.txt

# ── Layer 4: Face pipeline ──────────────────────────────────────────
COPY requirements-face.txt /tmp/requirements-face.txt
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --ignore-installed blinker -r /tmp/requirements-face.txt

# ── Layer 5: Voice pipeline ─────────────────────────────────────────
COPY requirements-voice.txt /tmp/requirements-voice.txt
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install -r /tmp/requirements-voice.txt || true
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install fairseq>=0.12.2 --no-deps || true

# ── Layer 6: Brain/cognition ────────────────────────────────────────
COPY requirements-brain.txt /tmp/requirements-brain.txt
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install -r /tmp/requirements-brain.txt

# ── Layer 7: cuDNN overlay (REMOVED — already in nvidia/cuda base image) ──

# ====================================================================
# STAGE 3: Runtime (slim — no build tools, no PPA, no dev packages)
# ====================================================================
FROM nvidia/cuda:${CUDA_VERSION}-runtime-${UBUNTU_VERSION} AS runtime

ARG PYTHON_VERSION

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TF_ENABLE_ONEDNN_OPTS=0 \
    KMP_DUPLICATE_LIB_OK=TRUE \
    DEBIAN_FRONTEND=noninteractive

# Install deadsnakes PPA + runtime essentials
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y --no-install-recommends \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    curl \
    ffmpeg \
    libgl1 \
    libegl1 \
    libgles2 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set up python symlinks
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python${PYTHON_VERSION} 1

# Copy all installed Python packages from pydeps stage (both libs and binaries)
COPY --from=pydeps /usr/local/lib/python${PYTHON_VERSION}/ /usr/local/lib/python${PYTHON_VERSION}/
COPY --from=pydeps /usr/local/bin/ /usr/local/bin/

# Copy the application source code
COPY . /app/dreamtalk/

# Create runtime directories
RUN mkdir -p /app/pipeline_outputs/tts

WORKDIR /app

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl --fail http://localhost:5000/health || exit 1

CMD ["uvicorn", "dreamtalk.backend.main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]
