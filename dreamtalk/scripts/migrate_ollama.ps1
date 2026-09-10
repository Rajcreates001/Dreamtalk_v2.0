# Migrate Ollama models from C: to D: drive
Write-Host "=== Migrating Ollama Models to D: Drive ===" -ForegroundColor Cyan

$source = "C:\Users\Maharaj\.ollama\models"
$dest = "D:\OllamaModels"
$ollamaDir = "C:\Users\Maharaj\.ollama"

# Step 1: Check source exists
Write-Host "`n[1/5] Checking source..." -ForegroundColor Yellow
if (!(Test-Path $source)) {
    Write-Host "ERROR: Source not found: $source" -ForegroundColor Red
    exit 1
}
$sourceSize = (Get-ChildItem $source -Recurse -File | Measure-Object -Property Length -Sum).Sum
Write-Host "Source found: $source ($([Math]::Round($sourceSize/1MB, 2)) MB)"

# Step 2: Create destination
Write-Host "`n[2/5] Creating destination..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $dest | Out-Null
New-Item -ItemType Directory -Force -Path "$dest\blobs" | Out-Null
Write-Host "Destination ready: $dest"

# Step 3: Copy models using Robocopy
Write-Host "`n[3/5] Copying files..." -ForegroundColor Yellow
$robocopyArgs = @($source, $dest, "/E", "/COPY:DAT", "/R:2", "/W:3", "/NP")
$result = Start-Process -Wait -NoNewWindow -FilePath "robocopy" -ArgumentList $robocopyArgs -PassThru
Write-Host "Robocopy exit code: $($result.ExitCode) (0-7 = success)" -ForegroundColor Green

# Step 4: Set OLLAMA_MODELS environment variable (User scope)
Write-Host "`n[4/5] Setting OLLAMA_MODEMS env var..." -ForegroundColor Yellow
[Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $dest, "User")
$env:OLLAMA_MODELS = $dest
Write-Host "OLLAMA_MODELS = $dest" -ForegroundColor Green

# Keep a backup indicator in the old location
Write-Host "`n[5/5] Creating backup marker..." -ForegroundColor Yellow
$marker = "$ollamaDir\MIGRATED_TO_D_DRIVE.txt"
"Migrated to D:\OllamaModels on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $marker
Write-Host "Marker created: $marker" -ForegroundColor Green

# Summary
Write-Host "`n=== Migration Complete ===" -ForegroundColor Cyan
Write-Host "Models moved from: $source" -ForegroundColor Green
Write-Host "Models now at:     $dest" -ForegroundColor Green
Write-Host "OLLAMA_MODELS:     $env:OLLAMA_MODELS" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Restart Ollama (kill it from system tray, then relaunch)" -ForegroundColor White
Write-Host "2. Verify: ollama list" -ForegroundColor White
Write-Host "3. Test: ollama run llama3.1:8b 'Hello!'" -ForegroundColor White
