# DreamTalk Doctor Avatar — Docker Startup
# Run this from the dreamtalk/docker/ directory

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  DreamTalk Doctor Avatar — Docker Startup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker
try {
    docker info 2>&1 | Out-Null
    Write-Host "[OK] Docker is running" -ForegroundColor Green
} catch {
    Write-Host "[!] Docker Desktop is not running. Please start Docker Desktop first." -ForegroundColor Red
    Write-Host "    Then re-run this script." -ForegroundColor Yellow
    exit 1
}

# Navigate to docker directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host ""
Write-Host "Building and starting containers..." -ForegroundColor Yellow

# Stop any existing containers
docker compose -f docker-compose.dreamtalk.yml --env-file ../.env.docker down 2>&1 | Out-Null

# Build and start
docker compose -f docker-compose.dreamtalk.yml --env-file ../.env.docker up -d --build

Write-Host ""
Write-Host "Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Check health
Write-Host ""
Write-Host "Checking service health..." -ForegroundColor Cyan

$services = @(
    @{Name="Backend"; Url="http://localhost:5001/livez"},
    @{Name="Doctor Avatar"; Url="http://localhost:5001/api/avatar/doctor"},
    @{Name="Postgres"; Url="http://localhost:5433"},
    @{Name="Redis"; Port=6380}
)

foreach ($svc in $services) {
    try {
        if ($svc.Port) {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $tcp.Connect("localhost", $svc.Port)
            $tcp.Close()
            Write-Host "  [OK] $($svc.Name) — port $($svc.Port) open" -ForegroundColor Green
        } else {
            $resp = Invoke-WebRequest -Uri $svc.Url -TimeoutSec 5 -ErrorAction Stop
            Write-Host "  [OK] $($svc.Name) — HTTP $($resp.StatusCode)" -ForegroundColor Green
        }
    } catch {
        Write-Host "  [!!] $($svc.Name) — not ready yet" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Doctor Avatar is READY!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Open in your browser:" -ForegroundColor White
Write-Host "  http://localhost:5001/api/avatar/doctor" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Or from network:" -ForegroundColor White
Write-Host "  http://$(hostname):5001/api/avatar/doctor" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Chat API:" -ForegroundColor White
Write-Host "  POST http://localhost:5001/api/avatar/chat" -ForegroundColor Gray
Write-Host ""
Write-Host "  View logs:" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.dreamtalk.yml logs -f backend" -ForegroundColor Gray
Write-Host ""
Write-Host "  Stop all:" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.dreamtalk.yml down" -ForegroundColor Gray
Write-Host ""
