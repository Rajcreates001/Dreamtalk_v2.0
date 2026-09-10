# Deployment Guide - Svara TTS API (adapted from Kenpath/svara-tts)

This guide provides comprehensive instructions for deploying the Svara TTS API with the embedded vLLM engine in a Docker container.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Building the Image](#building-the-image)
- [Running the Container](#running-the-container)
- [API Usage](#api-usage)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)

## Prerequisites

### Required Software

1. **Docker** (version 20.10 or later)
   ```bash
   docker --version
   ```

2. **Docker Compose** (version 2.0 or later)
   ```bash
   docker-compose --version
   ```

3. **NVIDIA GPU Drivers** (for GPU acceleration)
   ```bash
   nvidia-smi
   ```

4. **NVIDIA Container Toolkit**
   ```bash
   # Install on Ubuntu/Debian
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
     sudo tee /etc/apt/sources.list.d/nvidia-docker.list

   sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```

### Hardware Requirements

- **Minimum**:
  - GPU: NVIDIA GPU with 16GB VRAM (e.g., Tesla T4, RTX 4070)
  - RAM: 16GB system RAM
  - Storage: 50GB free space

- **Recommended**:
  - GPU: NVIDIA GPU with 24GB+ VRAM (e.g., A100, RTX 4090, H100)
  - RAM: 32GB system RAM
  - Storage: 100GB free space (for model cache)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd svara-tts-inference
```

### 2. Configure Environment Variables

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration (optional)
nano .env
```

### 3. Build and Run

```bash
# Build the Docker image
docker-compose build

# Start the service
docker-compose up -d

# Check logs
docker-compose logs -f
```

### 4. Verify Deployment

```bash
# Check health
curl http://localhost:8080/health

# List available voices
curl http://localhost:8080/v1/voices

# Test text-to-speech
