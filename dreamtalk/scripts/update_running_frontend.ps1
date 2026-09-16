<# Update application artifacts in the existing container; never builds an image.
   Run again after container recreation, which discards its writable layer.
   Dependencies must already match the installed container dependencies. #>
param([switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$frontendRoot = Join-Path $projectRoot 'frontend'
$containerName = 'dreamtalk-frontend'

function Invoke-DockerChecked {
    param([string[]]$Arguments)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed: $($Arguments[0])" }
}

$originalImage = Invoke-DockerChecked @('inspect', '--format', '{{.Image}}', $containerName)
if (-not $SkipBuild) {
    Push-Location $frontendRoot
    try {
        & npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed; container was not updated.' }
    } finally { Pop-Location }
}
$buildRoot = Join-Path $frontendRoot '.next'
foreach ($required in @('BUILD_ID', 'server', 'static', 'required-server-files.json')) {
    if (-not (Test-Path -LiteralPath (Join-Path $buildRoot $required))) {
        throw "Missing production artifact: $required"
    }
}
# Retain older static chunks so already-open browser tabs keep working.
foreach ($directory in @('static', 'server')) {
    Write-Output "Updating frontend $directory artifacts..."
    Invoke-DockerChecked @('cp', ((Join-Path $buildRoot $directory) + '/.'),
        "${containerName}:/app/.next/$directory/")
}
Get-ChildItem -LiteralPath $buildRoot -File |
    Where-Object { $_.Extension -eq '.json' -or $_.Name -eq 'BUILD_ID' } |
    ForEach-Object {
        Invoke-DockerChecked @('cp', $_.FullName, "${containerName}:/app/.next/$($_.Name)")
    }
Invoke-DockerChecked @('restart', $containerName)
$deadline = (Get-Date).AddMinutes(3)
do {
    $health = Invoke-DockerChecked @('inspect', '--format', '{{.State.Health.Status}}', $containerName)
    if ($health -eq 'healthy') { break }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)
if ($health -ne 'healthy') { throw "Frontend health check did not pass: $health" }
$currentImage = Invoke-DockerChecked @('inspect', '--format', '{{.Image}}', $containerName)
if ($currentImage -ne $originalImage) { throw 'Container image changed during update.' }
Write-Output 'Frontend updated and healthy; Docker image unchanged.'
