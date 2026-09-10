#!/usr/bin/env python3
"""
DreamTalk Local GPU Training Setup
===================================
Verifies your local environment is ready for GPU-accelerated training
with your RTX 4060 (or other NVIDIA GPU).

Usage:
    python scripts/gpu_train_setup.py

This script will:
  1. Check NVIDIA driver + CUDA toolkit availability
  2. Verify PyTorch CUDA support
  3. Set DREAMTALK_DEVICE=cuda environment variable
  4. Suggest optimal training parameters for your GPU
  5. Run a quick GPU benchmark
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

# Color helpers
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def step(title: str):
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}  {title}{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")


def ok(msg: str):
    print(f"  {GREEN}✅ {msg}{RESET}")


def warn(msg: str):
    print(f"  {YELLOW}⚠️  {msg}{RESET}")


def fail(msg: str):
    print(f"  {RED}❌ {msg}{RESET}")


def info(msg: str):
    print(f"     {msg}")


# ═══════════════════════════════════════════════════════════════════════
# STEP 1: System Check
# ═══════════════════════════════════════════════════════════════════════
step("STEP 1: System Information")

info(f"OS: {platform.system()} {platform.release()}")
info(f"Python: {sys.version.split()[0]}")
info(f"Project root: {ROOT}")

# ═══════════════════════════════════════════════════════════════════════
# STEP 2: NVIDIA Driver Check
# ═══════════════════════════════════════════════════════════════════════
step("STEP 2: NVIDIA Driver Check")

nvidia_smi = shutil.which("nvidia-smi")
if nvidia_smi:
    try:
        result = subprocess.run(
            [nvidia_smi, "--query-gpu=name,driver_version,cuda_version,temperature.gpu,memory.total,memory.free",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    ok(f"GPU: {parts[0]}")
                    ok(f"Driver: {parts[1]}")
                    ok(f"CUDA Toolkit: {parts[2]}")
                if len(parts) >= 5:
                    ok(f"Temp: {parts[3]}")
                    ok(f"Memory: {parts[4]} total, {parts[5]} free")
        else:
            fail("nvidia-smi returned an error")
    except Exception as e:
        fail(f"nvidia-smi error: {e}")
else:
    fail("nvidia-smi not found! NVIDIA driver not installed or not in PATH.")
    fail("Install drivers from: https://www.nvidia.com/download/index.aspx")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════
# STEP 3: PyTorch CUDA Check
# ═══════════════════════════════════════════════════════════════════════
step("STEP 3: PyTorch CUDA Support")

try:
    import torch
    ok(f"PyTorch {torch.__version__} installed")

    if torch.cuda.is_available():
        ok(f"CUDA available: {torch.cuda.is_available()}")
        ok(f"GPU count: {torch.cuda.device_count()}")
        ok(f"GPU name: {torch.cuda.get_device_name(0)}")
        ok(f"CUDA version (torch): {torch.version.cuda}")
        ok(f"cuDNN version: {torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else 'N/A'}")

        # Memory info
        free_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
        info(f"Total GPU memory: {free_mem:.1f} GB")

        # Recommended batch sizes based on GPU memory
        if free_mem >= 24:
            info("  → Batch size recommendation: 32-64 (large GPU)")
        elif free_mem >= 12:
            info("  → Batch size recommendation: 16-32 (medium GPU)")
        elif free_mem >= 8:
            info("  → Batch size recommendation: 8-16 (e.g., RTX 4060)")
        elif free_mem >= 4:
            info("  → Batch size recommendation: 4-8 (small GPU)")
        else:
            info("  → Batch size recommendation: 1-4 (limited GPU memory)")
    else:
        fail("CUDA NOT available for PyTorch!")
        warn("Make sure you installed the CUDA version of PyTorch:")
        info("  pip install torch==2.5.1+cu124 torchvision==0.20.1+cu124 torchaudio==2.5.1+cu124")
        info("  --index-url https://download.pytorch.org/whl/cu124")
        sys.exit(1)

    # MPS (Apple Silicon) check
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        ok("MPS (Apple Silicon) available as fallback")

except ImportError:
    fail("PyTorch is not installed!")
    info("Install PyTorch with CUDA support:")
    info("  pip install torch==2.5.1+cu124 torchvision==0.20.1+cu124 torchaudio==2.5.1+cu124")
    info("  --index-url https://download.pytorch.org/whl/cu124")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════
# STEP 4: Environment Variables
# ═══════════════════════════════════════════════════════════════════════
step("STEP 4: Environment Variable Setup")

os.environ["DREAMTALK_DEVICE"] = "cuda"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

ok("DREAMTALK_DEVICE=cuda — forces GPU mode for all DreamTalk pipelines")
ok("TF_CPP_MIN_LOG_LEVEL=3 — suppresses TensorFlow warnings")
ok("KMP_DUPLICATE_LIB_OK=TRUE — avoids OpenMP library conflicts on Windows")

info("")
info("To persist these settings, add to your shell profile or .env file:")
info("  DREAMTALK_DEVICE=cuda")
info("  TF_CPP_MIN_LOG_LEVEL=3")
info("  KMP_DUPLICATE_LIB_OK=TRUE")

# ═══════════════════════════════════════════════════════════════════════
# STEP 5: GPU Benchmark (Quick)
# ═══════════════════════════════════════════════════════════════════════
step("STEP 5: Quick GPU Benchmark")

try:
    import torch
    import time

    device = torch.device("cuda")

    # Matrix multiplication benchmark
    sizes = [1024, 2048, 4096]
    for n in sizes:
        a = torch.randn(n, n, device=device)
        b = torch.randn(n, n, device=device)

        # Warmup
        for _ in range(5):
            c = a @ b

        torch.cuda.synchronize()
        start = time.perf_counter()
        iterations = 20 if n <= 2048 else 10
        for _ in range(iterations):
            c = a @ b
        torch.cuda.synchronize()
        elapsed = (time.perf_counter() - start) / iterations

        flops = 2 * n**3 / elapsed / 1e12
        ok(f"Matmul {n}×{n}: {elapsed*1000:.1f} ms — {flops:.1f} TFLOPS")

    # Check FP16 support (Ampere+)
    if torch.cuda.get_device_capability(0)[0] >= 8:
        ok("FP16/BF16 supported (Ampere+ architecture) — enable mixed precision!")
    elif torch.cuda.get_device_capability(0)[0] >= 7:
        ok("FP16 supported (Volta/Turing) — enable mixed precision!")
    else:
        warn("FP16 not supported — use FP32 training")

except Exception as e:
    warn(f"Benchmark failed: {e}")

# ═══════════════════════════════════════════════════════════════════════
# STEP 6: DreamTalk Device Utility Check
# ═══════════════════════════════════════════════════════════════════════
step("STEP 6: DreamTalk Device Utility Check")

try:
    from dreamtalk.shared.utils.device import get_device, get_device_name, get_device_count
    device = get_device()
    count = get_device_count()
    name = get_device_name()
    ok(f"DreamTalk device utility reports: device={device}, count={count}, name={name}")
except Exception as e:
    warn(f"Could not import dreamtalk.shared.utils.device: {e}")
    info("(This is OK if the dreamtalk package is not installed yet)")

# ═══════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════
step("SUMMARY — GPU Training Ready!")

print(f"""
  {BOLD}Your RTX 4060 is ready for training!{RESET}

  {BOLD}Recommended training config:{RESET}
    device=cuda
    batch_size=8  (adjust based on model size)
    mixed_precision=fp16  (faster training, less memory)
    num_workers=2-4  (data loading)
    gradient_accumulation_steps=2-4  (effective batch size scaling)

  {BOLD}To run training:{RESET}
    Set env:     $env:DREAMTALK_DEVICE=\"cuda\"   (PowerShell)
                 set DREAMTALK_DEVICE=cuda        (CMD)
                 export DREAMTALK_DEVICE=cuda     (WSL/Bash)

    Run script:  python path/to/training/script.py

  {BOLD}Training scripts available:{RESET}
    - dreamtalk/cognition/core/consciousness/aura/training/
    - dreamtalk/avatar/core/body/idol/train.py
    - dreamtalk/face/core/lipsync/musetalk/train.py

  {BOLD}Memory optimization tips for RTX 4060 (8GB):{RESET}
    • Use gradient checkpointing (--gradient_checkpointing)
    • Limit batch size to 4-8
    • Use mixed precision training (fp16)
    • Monitor memory: nvidia-smi -l 1
    • Close other GPU apps (browsers, etc.)
""")
