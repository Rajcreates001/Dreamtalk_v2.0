# ── Dreamtalk Podman Helper (Windows PowerShell) ───────────────────────
#
# This script wraps Podman commands to run inside the WSL2 Ubuntu distro.
#
# Why Podman instead of Docker?
#   ✅ Daemonless architecture — lower memory/CPU usage
#   ✅ Rootless by default — stronger security isolation
#   ✅ Smaller storage footprint — no Docker Desktop overhead
#   ✅ Full GPU passthrough via NVIDIA CDI
#   ✅ Drop-in docker-compose compatible
#
# Usage:
#   .\run_podman.ps1 [up|down|logs|rebuild|status|shell|prune|gpu-test]
#
# Prerequisites:
#   - Podman installed in WSL2 Ubuntu (run `.\run_podman.ps1 shell` to access)
#   - NVIDIA Container Toolkit installed (for GPU support)
#   - WSL2 with Ubuntu distro configured
# ───────────────────────────────────────────────────────────────────────

param(
    [string]$Action = "up"
)

$ROOT = "D:\Black folder\DreamTalk_Startup\Dreamtalk-Integrated"
$WSL_ROOT = '/mnt/d/Black\ folder/DreamTalk_Startup/Dreamtalk-Integrated'

switch ($Action) {
    "up" {
        Write-Host "Starting ALL Dreamtalk services with Podman (WSL2)..." -ForegroundColor Cyan
        wsl -d Ubuntu --cd "$WSL_ROOT" bash -c "podman compose -f docker/podman-compose.yml up -d"
        Write-Host "Dreamtalk started with Podman!" -ForegroundColor Green
        $WSL_IP = wsl -d Ubuntu bash -c "hostname -I" 2>$null
        Write-Host "  Use 'localhost' (Docker-compatible via portproxy if set up)" -ForegroundColor Yellow
    }
    "up:infra" {
        Write-Host "Starting infrastructure only (PostgreSQL, Redis, Weaviate) with Podman..." -ForegroundColor Cyan
        Write-Host "  Backend runs directly: python run_server.py" -ForegroundColor DarkGray
        Write-Host "  Storage: D:\podman-data\ (created by setup_drive.ps1)" -ForegroundColor DarkGray
        wsl -d Ubuntu --cd "$WSL_ROOT" bash -c "podman compose -f docker/podman-compose.infra.yml up -d"
        Write-Host "Infrastructure started!" -ForegroundColor Green
        Write-Host "  PostgreSQL: localhost:5432" -ForegroundColor Yellow
        Write-Host "  Redis:      localhost:6379" -ForegroundColor Yellow
        Write-Host "  Weaviate:   localhost:8080" -ForegroundColor Yellow
    }
    "down" {
        Write-Host "Stopping Dreamtalk (Podman)..." -ForegroundColor Cyan
        wsl -d Ubuntu --cd "$WSL_ROOT" bash -c "podman compose -f docker/podman-compose.yml down"
        Write-Host "Dreamtalk stopped." -ForegroundColor Green
    }
    "down:infra" {
        Write-Host "Stopping infrastructure (Podman)..." -ForegroundColor Cyan
        wsl -d Ubuntu --cd "$WSL_ROOT" bash -c "podman compose -f docker/podman-compose.infra.yml down"
        Write-Host "Infrastructure stopped." -ForegroundColor Green
    }
    "logs" {
        wsl -d Ubuntu --cd "$WSL_ROOT" bash -c "podman compose logs -f"
    }
    "rebuild" {
        Write-Host "Rebuilding Dreamtalk with Podman..." -ForegroundColor Cyan
        wsl -d Ubuntu --cd "$WSL_ROOT" bash -c "podman compose down && podman compose build --no-cache && podman-compose up -d"
        Write-Host "Dreamtalk rebuilt and started!" -ForegroundColor Green
    }
    "status" {
        Write-Host "Podman Status:" -ForegroundColor Cyan
        wsl -d Ubuntu bash -c "podman info --format 'Rootless: {{.Host.Security.Rootless}} | CGroup: {{.Host.CGroupManager}} | Events: {{.Host.EventLogger}}' 2>/dev/null || echo 'checking...'"
        Write-Host "`nContainers:" -ForegroundColor Cyan
        wsl -d Ubuntu --cd "$WSL_ROOT" bash -c "podman compose ps"
        Write-Host "`nGPU Status:" -ForegroundColor Cyan
        wsl -d Ubuntu bash -c "nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu --format=csv,noheader 2>/dev/null || echo 'GPU not detected'"
        Write-Host "`nWSL2 IP:" -ForegroundColor Cyan
        $WSL_IP = wsl -d Ubuntu bash -c "hostname -I" 2>$null
        Write-Host "  $WSL_IP" -ForegroundColor Yellow
    }
    "shell" {
        Write-Host "Opening Podman shell (WSL2 Ubuntu)..." -ForegroundColor Cyan
        wsl -d Ubuntu --cd "$WSL_ROOT"
    }
    "prune" {
        Write-Host "Pruning unused Podman resources..." -ForegroundColor Cyan
        wsl -d Ubuntu bash -c "podman system prune -af --volumes"
        Write-Host "Prune complete." -ForegroundColor Green
    }
    "gpu-test" {
        Write-Host "Testing GPU passthrough in Podman..." -ForegroundColor Cyan
        wsl -d Ubuntu bash -c "podman run --rm --device nvidia.com/gpu=all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi"
    }
    "pull" {
        Write-Host "Pre-pulling images..." -ForegroundColor Cyan
        wsl -d Ubuntu bash -c "podman pull postgres:16-alpine && podman pull redis:7-alpine && podman pull semitechnologies/weaviate:latest"
        Write-Host "Images pulled." -ForegroundColor Green
    }
    default {
        Write-Host "Usage: .\run_podman.ps1 [up|down|up:infra|down:infra|logs|rebuild|status|shell|prune|gpu-test|pull]" -ForegroundColor Yellow
        Write-Host "`nCommands:" -ForegroundColor White
        Write-Host "  up         Start ALL services (full stack)" -ForegroundColor Gray
        Write-Host "  down       Stop ALL services" -ForegroundColor Gray
        Write-Host "  up:infra   Start INFRA ONLY (postgres, redis, weaviate) — backend runs locally" -ForegroundColor Gray
        Write-Host "  down:infra Stop infra only" -ForegroundColor Gray
        Write-Host "  logs       Follow logs" -ForegroundColor Gray
        Write-Host "  rebuild    Rebuild and restart" -ForegroundColor Gray
        Write-Host "  status     Show container and GPU status" -ForegroundColor Gray
        Write-Host "  shell      Open interactive WSL2 shell" -ForegroundColor Gray
        Write-Host "  prune      Clean up unused resources" -ForegroundColor Gray
        Write-Host "  gpu-test   Test GPU passthrough" -ForegroundColor Gray
        Write-Host "  pull       Pre-pull container images" -ForegroundColor Gray
        Write-Host "`nNote: Uses 'podman compose' (built-in, no hyphen, Podman >= 4.0)" -ForegroundColor DarkGray
        Write-Host "      For older Podman, use the hyphenated 'podman-compose' instead." -ForegroundColor DarkGray
        Write-Host "`nStorage: All persistent data goes to D:\podman-data\ (D: drive)" -ForegroundColor Cyan
        Write-Host "         Run docker/setup_drive.ps1 first to create directories" -ForegroundColor DarkGray
    }
}
