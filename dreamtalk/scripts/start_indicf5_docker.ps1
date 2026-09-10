<#
.SYNOPSIS
    Build and run the IndicF5 voice cloning microservice in Docker.

.DESCRIPTION
    This script builds the IndicF5 Docker image and runs it as a container.
    The weights directory is mounted from the D: drive to avoid copying
    the 1.34 GB model into the image.

.PARAMETER Action
    "build" — Build the Docker image (run once, or when code changes)
    "start" — Start the container (default)
    "stop"  — Stop the container
    "restart" — Restart the container
    "logs"  — Show container logs

.EXAMPLE
    .\scripts\start_indicf5_docker.ps1 build
    .\scripts\start_indicf5_docker.ps1 start
    .\scripts\start_indicf5_docker.ps1 stop
#>

param(
    [ValidateSet("build", "start", "stop", "restart", "logs", "status")]
    [string]$Action = "start"
)

$IMAGE_NAME = "dreamtalk-indicf5"
$CONTAINER_NAME = "dreamtalk-indicf5"
$HOST_PORT = 8002
$CONTAINER_PORT = 8002

# ── Find project root (where docker/ and weights/ directories live) ──
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Resolve-Path "$SCRIPT_DIR\.."
$WEIGHTS_DIR = "$PROJECT_ROOT\weights"

# ── Actions ──────────────────────────────────────────────────────────

function Build-Image {
    Write-Host "🔨 Building IndicF5 Docker image..." -ForegroundColor Cyan
    docker build -t $IMAGE_NAME -f "$PROJECT_ROOT\docker\Dockerfile.indicf5" "$PROJECT_ROOT"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Image built: $IMAGE_NAME" -ForegroundColor Green
    } else {
        Write-Host "❌ Build failed" -ForegroundColor Red
        exit 1
    }
}

function Start-Container {
    # Check if already running
    $existing = docker ps -a --filter "name=$CONTAINER_NAME" --format "{{.Names}}" 2>$null
    if ($existing) {
        $status = docker ps --filter "name=$CONTAINER_NAME" --format "{{.Status}}" 2>$null
        if ($status) {
            Write-Host "✅ Container $CONTAINER_NAME is already running ($status)" -ForegroundColor Green
            return
        }
        Write-Host "🗑️  Removing existing container..." -ForegroundColor Yellow
        docker rm $CONTAINER_NAME 2>$null
    }

    Write-Host "🚀 Starting IndicF5 microservice..." -ForegroundColor Cyan
    Write-Host "   Image: $IMAGE_NAME"
    Write-Host "   Port:  $HOST_PORT → $CONTAINER_PORT"
    Write-Host "   Weights: $WEIGHTS_DIR → /app/weights"

    docker run -d --name $CONTAINER_NAME `
        --restart unless-stopped `
        -p "${HOST_PORT}:${CONTAINER_PORT}" `
        -v "${WEIGHTS_DIR}:/app/weights" `
        -e INDICF5_WEIGHTS_DIR=/app/weights/voice/indic_tts/IndicF5 `
        -e INDICF5_PORT=$CONTAINER_PORT `
        $IMAGE_NAME

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Container started!" -ForegroundColor Green
        Write-Host "   API: http://localhost:$HOST_PORT"
        Write-Host "   Health: http://localhost:$HOST_PORT/health"
    } else {
        Write-Host "❌ Failed to start container" -ForegroundColor Red
        exit 1
    }
}

function Stop-Container {
    Write-Host "🛑 Stopping IndicF5 container..." -ForegroundColor Yellow
    docker stop $CONTAINER_NAME 2>$null
    Write-Host "✅ Container stopped" -ForegroundColor Green
}

function Restart-Container {
    Stop-Container
    Start-Container
}

function Show-Logs {
    docker logs -f $CONTAINER_NAME
}

function Show-Status {
    $exists = docker ps -a --filter "name=$CONTAINER_NAME" --format "{{.Names}}" 2>$null
    if (-not $exists) {
        Write-Host "❌ Container $CONTAINER_NAME does not exist" -ForegroundColor Red
        return
    }
    $running = docker ps --filter "name=$CONTAINER_NAME" --format "{{.Status}}" 2>$null
    if ($running) {
        Write-Host "✅ $CONTAINER_NAME is running: $running" -ForegroundColor Green
        Write-Host "   API: http://localhost:$HOST_PORT/health"
        # Check health
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:$HOST_PORT/health" -UseBasicParsing -TimeoutSec 5
            $body = $resp.Content | ConvertFrom-Json
            Write-Host "   Model loaded: $($body.model_loaded)" -ForegroundColor $(if ($body.model_loaded -eq $true) { "Green" } else { "Yellow" })
            Write-Host "   Device: $($body.device)"
        } catch {
            Write-Host "   Health check: failed ($($_.Exception.Message))" -ForegroundColor Red
        }
    } else {
        Write-Host "⚠️  $CONTAINER_NAME exists but is not running" -ForegroundColor Yellow
    }
}

# ── Main ─────────────────────────────────────────────────────────────
switch ($Action) {
    "build"   { Build-Image }
    "start"   { Start-Container }
    "stop"    { Stop-Container }
    "restart" { Restart-Container }
    "logs"    { Show-Logs }
    "status"  { Show-Status }
}
