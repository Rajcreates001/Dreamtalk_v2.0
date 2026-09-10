<#
.SYNOPSIS
    Set up a dedicated Python virtual environment for IndicF5 on the D: drive.

.DESCRIPTION
    Creates a virtual environment at D:\venvs\indicf5 with CPU-only PyTorch
    and all dependencies needed for IndicF5 voice cloning. This avoids the
    Windows OpenMP DLL conflict (libomp.dll vs libiomp5md.dll) by running
    IndicF5 in an isolated subprocess.

    The venv is created on D: drive to save space on C: and keep models
    and tools co-located.

.PARAMETER Force
    If set, re-create the venv even if it already exists.

.EXAMPLE
    .\scripts\setup_indicf5_venv.ps1
    .\scripts\setup_indicf5_venv.ps1 -Force
#>

param([switch]$Force)

$VENV_DIR = "D:\venvs\indicf5"
$PROJECT_ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "╔═══════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  IndicF5 Venv Setup                              ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project root: $PROJECT_ROOT"
Write-Host "Venv target:  $VENV_DIR"
Write-Host ""

# ── Check Python ────────────────────────────────────────────────────
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    Write-Host "❌ Python not found. Please install Python 3.10 or 3.11." -ForegroundColor Red
    exit 1
}

$pyVer = & $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "Using Python: $python (v$pyVer)" -ForegroundColor Gray

# ── Create or re-create venv ───────────────────────────────────────
if (Test-Path "$VENV_DIR\Scripts\python.exe") {
    if ($Force) {
        Write-Host "🗑️  Removing existing venv (Force)..."
        Remove-Item -Recurse -Force "$VENV_DIR"
    } else {
        Write-Host "✅ Venv already exists at $VENV_DIR" -ForegroundColor Green
        Write-Host "   Run with -Force to re-create."
        & "$VENV_DIR\Scripts\python.exe" -c "import torch; print(f'   PyTorch {torch.__version__} (CPU)')" -ErrorAction SilentlyContinue
        exit 0
    }
}

Write-Host "🔨 Creating virtual environment at $VENV_DIR..." -ForegroundColor Yellow
& $python -m venv "$VENV_DIR"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to create venv" -ForegroundColor Red
    exit 1
}

$pip = "$VENV_DIR\Scripts\pip.exe"
$py = "$VENV_DIR\Scripts\python.exe"

Write-Host "   Upgrading pip..." -ForegroundColor Gray
& $pip install --upgrade pip setuptools wheel

Write-Host ""
Write-Host "📦 Installing CPU-only PyTorch..." -ForegroundColor Yellow
& $pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ PyTorch install failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "📦 Installing IndicF5 dependencies..." -ForegroundColor Yellow
& $pip install --no-cache-dir `
    "fastapi>=0.110.0" `
    "uvicorn[standard]>=0.29.0" `
    "accelerate>=0.33.0" `
    "cached_path" `
    "librosa" `
    "soundfile" `
    "safetensors" `
    "transformers>=4.40.0" `
    "vocos" `
    "x-transformers>=1.31.14" `
    "torchdiffeq" `
    "ema-pytorch>=0.5.2" `
    "tqdm>=4.65.0" `
    "jieba" `
    "pydub" `
    "numpy<2.0.0"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Dependency install failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Venv setup complete!" -ForegroundColor Green
Write-Host "   Python: $py"
Write-Host "   Pip:    $pip"
& $py -c "import torch; print(f'   PyTorch {torch.__version__} (CPU)')"
Write-Host ""

Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Build the Docker image (preferred):" -ForegroundColor Gray
Write-Host "     docker build -t dreamtalk-indicf5 -f docker/Dockerfile.indicf5 ."
Write-Host ""
Write-Host "  2. Or run the venv-based microservice directly:" -ForegroundColor Gray
Write-Host "     $py -m dreamtalk.voice.core.vc.indicf5_venv_runner --port 8002"
Write-Host ""
