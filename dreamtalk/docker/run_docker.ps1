# ── Dreamtalk Docker Helper ───────────────────────────────────────────
param(
    [string]$Action = "up",
    [switch]$Slim
)

$ROOT = "D:\Black folder\DreamTalk_Startup\Dreamtalk-Integrated"
$COMPOSE_FILE = if ($Slim) { "docker-compose.gpu.yml" } else { "docker-compose.yml" }

function Run-Compose { param([string]$Cmd)
    Set-Location $ROOT
    $fileFlag = if ($Slim) { "-f docker-compose.gpu.yml" } else { "" }
    Invoke-Expression "docker compose $fileFlag $Cmd"
}

switch ($Action) {
    "up" {
        Write-Host "Starting Dreamtalk with Docker ($COMPOSE_FILE)..." -ForegroundColor Cyan
        Run-Compose "up --build -d"
        Write-Host "Dreamtalk started!" -ForegroundColor Green
        Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Yellow
        Write-Host "  Backend:  http://localhost:5000" -ForegroundColor Yellow
        Write-Host "  API Docs: http://localhost:5000/docs" -ForegroundColor Yellow
        Write-Host "  Avatar:   http://localhost:5000/api/avatar/viewer" -ForegroundColor Yellow
    }
    "up:infra" {
        Write-Host "Starting INFRASTRUCTURE ONLY (PostgreSQL, Redis, Weaviate)..." -ForegroundColor Cyan
        Write-Host "  Storage: D:\docker-data\ (D: drive — no C: drive usage)" -ForegroundColor DarkGray
        Write-Host "  Backend runs directly: python run_server.py" -ForegroundColor DarkGray
        Set-Location $ROOT
        docker compose -f docker/docker-compose.infra.yml up -d
        Write-Host "Infrastructure started!" -ForegroundColor Green
        Write-Host "  PostgreSQL: localhost:5432" -ForegroundColor Yellow
        Write-Host "  Redis:      localhost:6379" -ForegroundColor Yellow
        Write-Host "  Weaviate:   localhost:8080" -ForegroundColor Yellow
    }
    "down" {
        Write-Host "Stopping Dreamtalk..." -ForegroundColor Cyan
        Run-Compose "down"
        Write-Host "Dreamtalk stopped." -ForegroundColor Green
    }
    "down:infra" {
        Write-Host "Stopping infrastructure..." -ForegroundColor Cyan
        Set-Location $ROOT
        docker compose -f docker/docker-compose.infra.yml down
        Write-Host "Infrastructure stopped." -ForegroundColor Green
    }
    "logs" {
        Run-Compose "logs -f"
    }
    "rebuild" {
        Write-Host "Rebuilding Dreamtalk..." -ForegroundColor Cyan
        Run-Compose "down"
        Run-Compose "build --no-cache"
        Run-Compose "up -d"
        Write-Host "Dreamtalk rebuilt and started!" -ForegroundColor Green
    }
    "status" {
        Run-Compose "ps"
    }
    "clean" {
        Write-Host "Pruning Docker system..." -ForegroundColor Cyan
        docker system prune -a --volumes -f
        Write-Host "Done. To compact WSL2 disk, run: wsl --shutdown && diskpart (then select vdisk + compact)" -ForegroundColor Yellow
    }
    default {
        Write-Host "Usage: .\run_docker.ps1 [-Slim] [up|up:infra|down|down:infra|logs|rebuild|status|clean]" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Commands:" -ForegroundColor White
        Write-Host "  up         Start FULL stack (backend + frontend + infra containers)" -ForegroundColor Gray
        Write-Host "  down       Stop full stack" -ForegroundColor Gray
        Write-Host "  up:infra   Start INFRA ONLY (postgres, redis, weaviate) — backend runs locally" -ForegroundColor Gray
        Write-Host "  down:infra Stop infra only" -ForegroundColor Gray
        Write-Host "  logs       Follow logs" -ForegroundColor Gray
        Write-Host "  rebuild    Rebuild and restart" -ForegroundColor Gray
        Write-Host "  status     Show container status" -ForegroundColor Gray
        Write-Host "  clean      Prune Docker system" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Options:" -ForegroundColor White
        Write-Host "  -Slim      Use GPU-optimized compose (no Weaviate/Celery)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Storage: All persistent data goes to D:\docker-data\ (D: drive)" -ForegroundColor Cyan
        Write-Host "         Run docker/setup_drive.ps1 first to create directories" -ForegroundColor DarkGray
    }
}
