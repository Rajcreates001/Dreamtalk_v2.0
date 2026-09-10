# ── Dreamtalk D: Drive Setup Script ────────────────────────────────────
# Run this in PowerShell as Administrator to prepare D: drive storage
# for container volumes (PostgreSQL, Redis, Weaviate).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File docker/setup_drive.ps1
# ───────────────────────────────────────────────────────────────────────

Write-Host "=== Dreamtalk D: Drive Setup ===" -ForegroundColor Cyan
Write-Host ""

# ── 1. Create D: drive directories ─────────────────────────────────────
$dirs = @(
    "D:\docker-data\postgres",
    "D:\docker-data\redis",
    "D:\docker-data\weaviate",
    "D:\podman-data\postgres",
    "D:\podman-data\redis",
    "D:\podman-data\weaviate"
)

Write-Host "Creating D: drive storage directories..." -ForegroundColor Yellow
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  ✅ Created: $dir" -ForegroundColor Green
    } else {
        Write-Host "  ✅ Exists:  $dir" -ForegroundColor DarkGray
    }
}

# ── 2. Set permissions (all users can write) ────────────────────────────
Write-Host ""
Write-Host "Setting permissions (everyone: modify)..." -ForegroundColor Yellow
foreach ($dir in $dirs) {
    if (Test-Path $dir) {
        try {
            $acl = Get-Acl $dir
            $rule = New-Object System.Security.AccessControl.FileSystemAccessRule("Everyone", "Modify", "ContainerInherit,ObjectInherit", "None", "Allow")
            $acl.SetAccessRule($rule)
            Set-Acl -Path $dir -AclObject $acl
            Write-Host "  ✅ Permissions set: $dir" -ForegroundColor Green
        } catch {
            Write-Host "  ⚠️  Could not set permissions on $dir (run as Admin)" -ForegroundColor Yellow
        }
    }
}

# ── 3. Check container runtimes ─────────────────────────────────────────
Write-Host ""
Write-Host "Checking container runtimes..." -ForegroundColor Yellow

$dockerPath = Get-Command "docker" -ErrorAction SilentlyContinue
$podmanPath = Get-Command "podman" -ErrorAction SilentlyContinue

if ($dockerPath) {
    Write-Host "  ✅ Docker CLI found: $($dockerPath.Source)" -ForegroundColor Green
    try {
        $dockerInfo = docker info --format "{{.ServerVersion}}" 2>$null
        if ($dockerInfo) {
            Write-Host "  ✅ Docker daemon running (v$dockerInfo)" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  Docker daemon NOT running. Start Docker Desktop first." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ⚠️  Docker daemon NOT running. Start Docker Desktop first." -ForegroundColor Yellow
    }
} else {
    Write-Host "  ❌ Docker CLI not found" -ForegroundColor Red
}

if ($podmanPath) {
    Write-Host "  ✅ Podman found: $($podmanPath.Source)" -ForegroundColor Green
} else {
    Write-Host "  ❌ Podman not found." -ForegroundColor Red
    Write-Host "     Install Podman Desktop: https://podman-desktop.io/downloads" -ForegroundColor Gray
}

# ── 4. Summary ──────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "  D: drive storage directories: READY" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host ""
Write-Host "  Option A — Docker:" -ForegroundColor Cyan
Write-Host "    1. Start Docker Desktop" -ForegroundColor Gray
Write-Host "    2. docker compose -f docker/docker-compose.infra.yml up -d" -ForegroundColor Gray
Write-Host ""
Write-Host "  Option B — Podman:" -ForegroundColor Cyan
Write-Host "    1. Install Podman Desktop from https://podman-desktop.io/downloads" -ForegroundColor Gray
Write-Host "    2. podman-compose -f docker/podman-compose.infra.yml up -d" -ForegroundColor Gray
Write-Host ""
Write-Host "  Option C — Direct PostgreSQL (no containers):" -ForegroundColor Cyan
Write-Host "    1. Install PostgreSQL from https://www.postgresql.org/download/windows/" -ForegroundColor Gray
Write-Host "    2. Create database: createdb -U postgres dream_talk_db" -ForegroundColor Gray
Write-Host ""
Write-Host "  Then run the backend:" -ForegroundColor White
Write-Host "    cd dreamtalk" -ForegroundColor Gray
Write-Host "    python run_server.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  Then run the frontend:" -ForegroundColor White
Write-Host "    cd dreamtalk/frontend" -ForegroundColor Gray
Write-Host "    npm run dev" -ForegroundColor Gray
