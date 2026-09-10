<#
.SYNOPSIS
    Set up a dedicated Python virtual environment for LivePortrait on the D: drive.

.DESCRIPTION
    Creates a virtual environment at D:\venvs\liveportrait with CPU-only PyTorch
    and all dependencies needed for LivePortrait face animation. This avoids the
    Windows OpenMP DLL conflict (libomp.dll vs libiomp5md.dll / fbgemm.dll) by
    running LivePortrait in an isolated subprocess.

    Can optionally reuse the existing IndicF5 venv at D:\venvs\indicf5 by
    installing the additional LivePortrait dependencies there.

.PARAMETER Force
    If set, re-create the venv even if it already exists.

.PARAMETER ReuseIndicF5
    If set, install LivePortrait deps into the existing D:\venvs\indicf5 venv
    instead of creating a new one.

.EXAMPLE
    .\scripts\setup_liveportrait_venv.ps1
    .\scripts\setup_liveportrait_venv.ps1 -ReuseIndicF5
    .\scripts\setup_liveportrait_venv.ps1 -Force
#>

param(
    [switch]$Force,
    [switch]$ReuseIndicF5
)

$VENV_DIR = "D:\venvs\liveportrait"
$INDICF5_VENV = "D:\venvs\indicf5"
$PROJECT_ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "╔═══════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  LivePortrait Venv Setup                         ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

if ($ReuseIndicF5 -and (Test-Path "$INDICF5_VENV\Scripts\python.exe")) {
    Write-Host "♻️  Reusing IndicF5 venv at $INDICF5_VENV" -ForegroundColor Yellow
    $VENV_DIR = $INDICF5_VENV
} else {
    Write-Host "Target venv: $VENV_DIR" -ForegroundColor Cyan
}

Write-Host "Project root: $PROJECT_ROOT"
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
if (-not $ReuseIndicF5 -or -not (Test-Path "$INDICF5_VENV\Scripts\python.exe")) {
    if (Test-Path "$VENV_DIR\Scripts\python.exe") {
        if ($Force) {
            Write-Host "🗑️  Removing existing venv (Force)..."
            Remove-Item -Recurse -Force "$VENV_DIR"
        } else {
            Write-Host "✅ Venv already exists at $VENV_DIR" -ForegroundColor Green
            Write-Host "   Run with -Force to re-create."
            & "$VENV_DIR\Scripts\python.exe" -c "import torch; print(f'   PyTorch {torch.__version__} (CPU)')" -ErrorAction SilentlyContinue
        }
    }

    if (-not (Test-Path "$VENV_DIR\Scripts\python.exe")) {
        Write-Host "🔨 Creating virtual environment at $VENV_DIR..." -ForegroundColor Yellow
        & $python -m venv "$VENV_DIR"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Failed to create venv" -ForegroundColor Red
            exit 1
        }

        Write-Host "   Upgrading pip..." -ForegroundColor Gray
        & "$VENV_DIR\Scripts\pip.exe" install --upgrade pip setuptools wheel

        Write-Host ""
        Write-Host "📦 Installing CPU-only PyTorch..." -ForegroundColor Yellow
        & "$VENV_DIR\Scripts\pip.exe" install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ PyTorch install failed" -ForegroundColor Red
            exit 1
        }
    }
}

$py = "$VENV_DIR\Scripts\python.exe"
$pip = "$VENV_DIR\Scripts\pip.exe"

Write-Host ""
Write-Host "📦 Installing LivePortrait dependencies..." -ForegroundColor Yellow
& $pip install --no-cache-dir `
    "opencv-python>=4.9.0" `
    "numpy<2.0.0" `
    "pyyaml>=6.0" `
    "timm>=0.9.0" `
    "rich>=13.0" `
    "scipy>=1.12.0" `
    "onnxruntime>=1.17.0" `
    "librosa" `
    "soundfile"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Dependency install failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Venv setup complete!" -ForegroundColor Green
Write-Host "   Python: $py"
& $py -c "import torch, cv2, yaml; print(f'   torch {torch.__version__} (CPU)'); import timm; print(f'   timm OK'); print(f'   opencv OK'); print(f'   pyyaml OK')" -ErrorAction SilentlyContinue
Write-Host ""

Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Test the venv runner:" -ForegroundColor Gray
Write-Host "     $py face/core/animation/liveportrait/liveportrait_venv_runner.py --help"
Write-Host ""
Write-Host "  2. Or run a quick animation test:" -ForegroundColor Gray
Write-Host "     $py face/core/animation/liveportrait/liveportrait_venv_runner.py ^"
Write-Host "         --source path/to/source.jpg ^"
Write-Host "         --driving path/to/driving.mp4 ^"
Write-Host "         --output output/animation.mp4"
Write-Host ""
