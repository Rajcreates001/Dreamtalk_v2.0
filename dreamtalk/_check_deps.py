"""Comprehensive dependency health check for all backend services.

Tests every import the DreamTalk backend actually uses and reports
which ones pass/fail, with actionable fix suggestions.
"""
import os
import sys
import time
import subprocess
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Fix torch DLL path
try:
    import torch
    _torch_lib = Path(torch.__file__).resolve().parent / "lib"
    if _torch_lib.exists():
        os.environ.setdefault("PATH", "")
        os.environ["PATH"] = str(_torch_lib) + os.pathsep + os.environ["PATH"]
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(_torch_lib))
            except Exception:
                pass
except ImportError:
    pass

PASS = 0
FAIL = 0
WARN = 0
results = []


def check(label: str, import_stmt: str, pip_pkg: str = None, critical: bool = False):
    """Try importing a module and report result."""
    global PASS, FAIL, WARN
    try:
        exec(import_stmt)
        results.append((label, "PASS", "", critical))
        PASS += 1
    except Exception as e:
        msg = str(e).split("\n")[0][:120]
        if pip_pkg:
            hint = f"  pip install {pip_pkg}"
        else:
            hint = "  (check installation)"
        results.append((label, "FAIL" if critical else "WARN", f"{msg}\n{hint}", critical))
        if critical:
            FAIL += 1
        else:
            WARN += 1


def section(title: str):
    results.append((f"\n--- {title} ---", "", "", False))


# ═══════════════════════════════════════════
# SECTION 1: Core Python & Server
# ═══════════════════════════════════════════
section("CORE PYTHON & SERVER")

check("Python version", "assert sys.version_info >= (3,10)", critical=True)
check("FastAPI", "from fastapi import FastAPI", "fastapi", critical=True)
check("Uvicorn", "import uvicorn", "uvicorn", critical=True)
check("Starlette", "import starlette", "starlette", critical=True)
check("Pydantic", "import pydantic", "pydantic", critical=True)
check("dotenv", "from dotenv import load_dotenv", "python-dotenv", critical=True)

# ═══════════════════════════════════════════
# SECTION 2: Database
# ═══════════════════════════════════════════
section("DATABASE")

check("asyncpg", "import asyncpg", "asyncpg")
check("SQLite3", "import sqlite3")
check("psycopg2", "import psycopg2", "psycopg2-binary")

# Test actual DB connection
import asyncio
async def _test_db():
    global WARN
    try:
        if "asyncpg" in sys.modules:
            try:
                pool = await asyncpg.create_pool(
                    host="localhost", port=5432,
                    user="postgres", password=os.environ.get("DB_PASSWORD", ""),
                    database="dream_talk_db",
                    timeout=3, min_size=1, max_size=1,
                )
                async with pool.acquire() as conn:
                    v = await conn.fetchval("SELECT 1")
                await pool.close()
                results.append(("PostgreSQL connection", "PASS", "", False))
            except Exception as e:
                results.append(("PostgreSQL connection", "WARN", str(e)[:80], False))
                WARN += 1
        else:
            results.append(("PostgreSQL connection", "SKIP", "asyncpg not loaded", False))
            WARN += 1
    except Exception as e:
        results.append(("PostgreSQL connection", "WARN", str(e)[:80], False))
        WARN += 1
asyncio.run(_test_db())

# ═══════════════════════════════════════════
# SECTION 3: Machine Learning (Torch & TF)
# ═══════════════════════════════════════════
section("MACHINE LEARNING")

check("PyTorch", "import torch", "torch", critical=True)
check("torch CUDA", "import torch; _ = torch.cuda.is_available()", critical=False)
check("torchvision", "import torchvision", "torchvision")
check("torchaudio", "import torchaudio", "torchaudio")
check("TensorFlow", "import tensorflow as tf; _ = tf.__version__", "tensorflow")
check("NumPy", "import numpy as np", "numpy", critical=True)
check("OpenCV", "import cv2", "opencv-python", critical=True)
check("SoundFile", "import soundfile as sf", "soundfile", critical=True)
check("SciPy", "import scipy", "scipy")
check("Scikit-learn", "import sklearn", "scikit-learn")
check("Librosa", "import librosa", "librosa")
check("Matplotlib", "import matplotlib", "matplotlib")

# ═══════════════════════════════════════════
# SECTION 4: Face Pipeline
# ═══════════════════════════════════════════
section("FACE PIPELINE")

check("MediaPipe", "import mediapipe as mp", "mediapipe")
check("DeepFace", "import deepface", "deepface")
check("FaceXLib", "import facexlib", "facexlib")
check("GFPGAN", "import gfpgan", "gfpgan")
check("BasicsR", "import basicsr", "basicsr")
check("InsightFace", "import insightface", "insightface")
check("TRIMesh", "import trimesh", "trimesh")
check("PyMeshLab", "import pymeshlab", "pymeshlab")
check("PyRender", "import pyrender", "pyrender")
check("Open3D", "import open3d", "open3d")

# Test FacePipeline import
check("FacePipeline class", 
    "from dreamtalk.pipeline.face_pipeline import FacePipeline",
    critical=False)

# ═══════════════════════════════════════════
# SECTION 5: Voice Pipeline
# ═══════════════════════════════════════════
section("VOICE PIPELINE")

check("Edge-TTS", "import edge_tts", "edge-tts", critical=True)
check("PyDub", "import pydub", "pydub")
check("PyWorld", "import pyworld", "pyworld")
check("Fairseq", "import fairseq", "fairseq")
check("FAISS", "import faiss", "faiss-cpu")
check("PyTorch Crepe", "import torchcrepe", "torchcrepe")
check("TTS (Coqui)", "import TTS", "TTS")
check("OpenVoice", "import openvoice", "openvoice")
check("Whisper", "import whisper", "openai-whisper")
check("Faster Whisper", "import faster_whisper", "faster-whisper")

# Test VoicePipeline import
check("VoicePipeline class",
    "from dreamtalk.pipeline.voice_pipeline import VoicePipeline",
    critical=False)

# ═══════════════════════════════════════════
# SECTION 6: Brain Pipeline
# ═══════════════════════════════════════════
section("BRAIN PIPELINE")

check("NLTK", "import nltk", "nltk")
check("VADER", "from nltk.sentiment import SentimentIntensityAnalyzer", "nltk vader_lexicon")
check("httpx", "import httpx", "httpx")
check("OpenAI", "import openai", "openai")

check("BrainPipeline class",
    "from dreamtalk.pipeline.brain_pipeline import BrainPipeline",
    critical=False)

# ═══════════════════════════════════════════
# SECTION 7: TTS Engines
# ═══════════════════════════════════════════
section("TTS ENGINES")

check("Edge-TTS (verify)", "import edge_tts; print(f'  Edge-TTS OK')", "edge-tts", critical=True)

# Kokoro TTS
try:
    import torch
    from pathlib import Path
    kokoro_weights = ROOT / "weights" / "kokoro"
    if kokoro_weights.exists():
        voices = list(kokoro_weights.glob("*.pt"))
        check(f"Kokoro voices ({len(voices)} files)", 
            f"assert {len(voices)} > 0", critical=False)
    else:
        results.append(("Kokoro weights dir", "WARN", "weights/kokoro/ not found", False))
        WARN += 1
except Exception as e:
    pass

check("Kokoro engine",
    "from dreamtalk.voice.core.tts.kokoro_engine import KokoroTTSEngine",
    critical=False)

# ═══════════════════════════════════════════
# SECTION 8: Full Orchestrator
# ═══════════════════════════════════════════
section("FULL ORCHESTRATOR")

check("PipelineOrchestrator",
    "from dreamtalk.pipeline.orchestrator import PipelineOrchestrator",
    critical=True)

check("PipelineRequest",
    "from dreamtalk.pipeline.models import PipelineRequest",
    critical=True)

check("StudentKnowledgeBase",
    "from dreamtalk.backend.services.knowledge_base import StudentKnowledgeBase",
    critical=True)

# ═══════════════════════════════════════════
# SECTION 9: Edge-TTS end-to-end test
# ═══════════════════════════════════════════
section("EDGE-TTS END-TO-END TEST")

async def _test_edgetts():
    global PASS, FAIL
    try:
        import edge_tts
        out = Path(str(ROOT)) / "pipeline_outputs" / "_test_tts.wav"
        os.makedirs(str(out.parent), exist_ok=True)
        c = edge_tts.Communicate("Hello, this is a test.", "en-US-JennyNeural")
        await c.save(str(out))
        size = out.stat().st_size
        os.remove(out)
        results.append((f"Edge-TTS generated audio ({size} bytes)", "PASS", "", True))
        PASS += 1
    except Exception as e:
        results.append((f"Edge-TTS end-to-end", "FAIL", str(e)[:80], True))
        FAIL += 1

asyncio.run(_test_edgetts())

# ═══════════════════════════════════════════
# SECTION 10: ALL DREAMTALK BACKEND IMPORTS
# ═══════════════════════════════════════════
section("BACKEND IMPORT INTEGRITY")

check("backend.main", "from dreamtalk.backend.main import app", critical=True)
check("avatar router", "from dreamtalk.backend.api.v1.endpoints.avatar import router", critical=True)
check("api_logger", "from dreamtalk.backend.services.api_logger import APILoggingMiddleware", critical=True)
check("knowledge_base", "from dreamtalk.backend.services.knowledge_base import StudentKnowledgeBase", critical=True)
check("chat endpoint", "from dreamtalk.backend.api.v1.endpoints.chat import router as chat_r", critical=True)
check("pipeline endpoint", "from dreamtalk.backend.api.v1.endpoints.pipeline import router as pipe_r", critical=True)


# ═══════════════════════════════════════════
# PRINT RESULTS
# ═══════════════════════════════════════════
print("\n" + "=" * 70)
print("  DREAMTALK DEPENDENCY HEALTH CHECK")
print("=" * 70)

for label, status, detail, critical in results:
    if not label:
        print()
        continue
    if status == "PASS":
        print(f"  [PASS] {label}")
    elif status == "FAIL":
        print(f"  [FAIL] {label}")
        if detail:
            print(f"         {detail}")
    elif status == "WARN":
        print(f"  [WARN] {label}")
        if detail:
            print(f"         {detail}")
    elif status == "SKIP":
        pass

print()
print("=" * 70)
print(f"  RESULTS: {PASS} passed, {WARN} warnings, {FAIL} failed")
print("=" * 70)

if FAIL > 0:
    print("\n  CRITICAL ISSUES TO FIX:")
    for label, status, detail, critical in results:
        if status == "FAIL":
            print(f"    - {label}: {detail}")
else:
    print("\n  All critical dependencies OK!")

print()
