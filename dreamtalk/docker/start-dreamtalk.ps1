# ═══════════════════════════════════════════════════════════════════════
# DreamTalk Docker Startup Script
# ═══════════════════════════════════════════════════════════════════════
# Usage:
#   .\start-dreamtalk.ps1 up          # Start all services
#   .\start-dreamtalk.ps1 up:build    # Rebuild images and start
#   .\start-dreamtalk.ps1 down        # Stop all services
#   .\start-dreamtalk.ps1 logs        # Follow logs
#   .\start-dreamtalk.ps1 status      # Show container status
#   .\start-dreamtalk.ps1 health      # Check health of all services
#   .\start-dreamtalk.ps1 rebuild     # Full rebuild from scratch
#   .\start-dreamtalk.ps1 clean       # Prune unused Docker resources
#   .\start-dreamtalk.ps1 volumes     # Show volume info
# ═══════════════════════════════════════════════════════════════════════

param(
    [string]$Action = "up"
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot  # dreamtalk/
$ComposeFile = Join-Path $PSScriptRoot "docker-compose.dreamtalk.yml"
$EnvFile     = Join-Path $PSScriptRoot ".env.docker"

function Invoke-Compose {
    param([string]$Args)
    docker compose -f $ComposeFile --env-file $EnvFile $Args
}

function Show-Info {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║         DreamTalk Docker Environment            ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Services:" -ForegroundColor White
    Write-Host "    Backend API:   http://localhost:5001" -ForegroundColor Yellow
    Write-Host "    API Docs:      http://localhost:5001/docs" -ForegroundColor Yellow
    Write-Host "    Frontend:      http://localhost:3000" -ForegroundColor Yellow
    Write-Host "    Avatar Viewer: http://localhost:5001/api/avatar/viewer" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Infrastructure:" -ForegroundColor White
    Write-Host "    PostgreSQL:    localhost:5433" -ForegroundColor DarkGray
    Write-Host "    Redis:         localhost:6380" -ForegroundColor DarkGray
    Write-Host "    Weaviate:      http://localhost:8081" -ForegroundColor DarkGray
    Write-Host "    Weaviate gRPC: localhost:50052" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  TTS Microservice:" -ForegroundColor White
    Write-Host "    IndicF5:       http://localhost:8002" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  Volume Info:" -ForegroundColor White
    Write-Host "    All data persists in Docker named volumes." -ForegroundColor DarkGray
    Write-Host "    To check: docker volume inspect dreamtalk-postgres" -ForegroundColor DarkGray
    Write-Host ""
}

switch ($Action) {
    "up" {
        Write-Host "Starting DreamTalk services..." -ForegroundColor Cyan
        Invoke-Compose "up -d"
        Show-Info
    }
    "up:build" {
        Write-Host "Building and starting DreamTalk services..." -ForegroundColor Cyan
        Invoke-Compose "up -d --build"
        Show-Info
    }
    "down" {
        Write-Host "Stopping DreamTalk services..." -ForegroundColor Cyan
        Invoke-Compose "down"
        Write-Host "All DreamTalk services stopped." -ForegroundColor Green
    }
    "logs" {
        Invoke-Compose "logs -f --tail=100"
    }
    "logs:backend" {
        Invoke-Compose "logs -f --tail=100 backend"
    }
    "status" {
        Write-Host "DreamTalk Container Status:" -ForegroundColor Cyan
        Invoke-Compose "ps"
        Write-Host ""
        Write-Host "Resource Usage:" -ForegroundColor Cyan
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" dreamtalk-postgres dreamtalk-redis dreamtalk-weaviate dreamtalk-backend dreamtalk-frontend dreamtalk-indicf5 2>$null
    }
    "health" {
        Write-Host "Checking health of all DreamTalk services..." -ForegroundColor Cyan
        Write-Host ""

        # PostgreSQL
        $pg = docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' dreamtalk-postgres 2>$null
        if ($pg -eq "healthy") { Write-Host "  ✅ PostgreSQL: $pg" -ForegroundColor Green }
        elseif ($pg) { Write-Host "  ⚠️  PostgreSQL: $pg" -ForegroundColor Yellow }
        else { Write-Host "  ❌ PostgreSQL: not running" -ForegroundColor Red }

        # Redis
        $rd = docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' dreamtalk-redis 2>$null
        if ($rd -eq "healthy") { Write-Host "  ✅ Redis: $rd" -ForegroundColor Green }
        elseif ($rd) { Write-Host "  ⚠️  Redis: $rd" -ForegroundColor Yellow }
        else { Write-Host "  ❌ Redis: not running" -ForegroundColor Red }

        # Weaviate
        $wv = docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' dreamtalk-weaviate 2>$null
        if ($wv -eq "healthy") { Write-Host "  ✅ Weaviate: $wv" -ForegroundColor Green }
        elseif ($wv) { Write-Host "  ⚠️  Weaviate: $wv" -ForegroundColor Yellow }
        else { Write-Host "  ❌ Weaviate: not running" -ForegroundColor Red }

        # Backend
        $be = docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' dreamtalk-backend 2>$null
        if ($be -eq "healthy") { Write-Host "  ✅ Backend: $be" -ForegroundColor Green }
        elseif ($be) { Write-Host "  ⚠️  Backend: $be" -ForegroundColor Yellow }
        else { Write-Host "  ❌ Backend: not running" -ForegroundColor Red }

        # Frontend
        $fe = docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' dreamtalk-frontend 2>$null
        if ($fe -eq "healthy") { Write-Host "  ✅ Frontend: $fe" -ForegroundColor Green }
        elseif ($fe) { Write-Host "  ⚠️  Frontend: $fe" -ForegroundColor Yellow }
        else { Write-Host "  ❌ Frontend: not running" -ForegroundColor Red }

        # IndicF5
        $if5 = docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' dreamtalk-indicf5 2>$null
        if ($if5 -eq "healthy") { Write-Host "  ✅ IndicF5: $if5" -ForegroundColor Green }
        elseif ($if5) { Write-Host "  ⚠️  IndicF5: $if5" -ForegroundColor Yellow }
        else { Write-Host "  ❌ IndicF5: not running" -ForegroundColor Red }

        # HTTP health check for backend
        Write-Host ""
        Write-Host "  HTTP Health Check:" -ForegroundColor White
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:5001/health" -TimeoutSec 5 -UseBasicParsing
            $health = $response.Content | ConvertFrom-Json
            Write-Host "  ✅ Backend HTTP: $($health.status)" -ForegroundColor Green
            Write-Host "     Database: $($health.database)" -ForegroundColor DarkGray
            Write-Host "     Redis:    $($health.redis)" -ForegroundColor DarkGray
            Write-Host "     Weaviate: $($health.weaviate)" -ForegroundColor DarkGray
        } catch {
            Write-Host "  ❌ Backend HTTP: unreachable" -ForegroundColor Red
        }
    }
    "rebuild" {
        Write-Host "Full rebuild: stopping, removing, rebuilding..." -ForegroundColor Cyan
        Invoke-Compose "down -v"
        Invoke-Compose "build --no-cache"
        Invoke-Compose "up -d"
        Show-Info
    }
    "clean" {
        Write-Host "Pruning DreamTalk Docker resources..." -ForegroundColor Cyan
        docker image prune -f
        docker container prune -f
        Write-Host "Done." -ForegroundColor Green
        Write-Host "Note: Named volumes are preserved. To remove them: docker volume rm dreamtalk-*" -ForegroundColor DarkGray
    }
    "volumes" {
        Write-Host "DreamTalk Docker Volumes:" -ForegroundColor Cyan
        docker volume ls --filter "name=dreamtalk" --format "table {{.Name}}\t{{.Driver}}\t{{.Mountpoint}}"
        Write-Host ""
        Write-Host "Detailed info:" -ForegroundColor White
        docker volume ls --filter "name=dreamtalk" -q | ForEach-Object {
            Write-Host ""
            Write-Host "  $_" -ForegroundColor Yellow
            docker volume inspect $_ --format "    Created: {{.CreatedAt}}\n    Scope: {{.Scope}}\n    Mountpoint: {{.Mountpoint}}"
        }
    }
    "db:shell" {
        Write-Host "Connecting to PostgreSQL..." -ForegroundColor Cyan
        docker exec -it dreamtalk-postgres psql -U postgres -d dream_talk_db
    }
    "redis:shell" {
        Write-Host "Connecting to Redis..." -ForegroundColor Cyan
        docker exec -it dreamtalk-redis redis-cli
    }
    default {
        Write-Host ""
        Write-Host "DreamTalk Docker Control" -ForegroundColor White
        Write-Host ""
        Write-Host "Usage: .\start-dreamtalk.ps1 <action>" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Actions:" -ForegroundColor White
        Write-Host "  up          Start all services" -ForegroundColor Gray
        Write-Host "  up:build    Rebuild images and start" -ForegroundColor Gray
        Write-Host "  down        Stop all services" -ForegroundColor Gray
        Write-Host "  logs        Follow all logs" -ForegroundColor Gray
        Write-Host "  logs:backend Follow backend logs only" -ForegroundColor Gray
        Write-Host "  status      Show container status and resource usage" -ForegroundColor Gray
        Write-Host "  health      Check health of all services" -ForegroundColor Gray
        Write-Host "  rebuild     Full rebuild from scratch (removes volumes)" -ForegroundColor Gray
        Write-Host "  clean       Prune unused Docker resources" -ForegroundColor Gray
        Write-Host "  volumes     Show volume information" -ForegroundColor Gray
        Write-Host "  db:shell    Open PostgreSQL interactive shell" -ForegroundColor Gray
        Write-Host "  redis:shell Open Redis interactive shell" -ForegroundColor Gray
    }
}
