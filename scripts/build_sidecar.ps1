# Build PyInstaller FastAPI sidecar (onedir) for Tauri bundle.resources (ADR-008).
# Usage (from anywhere):  pwsh -File scripts/build_sidecar.ps1

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

Write-Host "==> uv sync --group packaging"
uv sync --group packaging

$DistDir = Join-Path $RepoRoot "packaging\dist\sentrealm-api"
$WorkDir = Join-Path $RepoRoot "packaging\build"
$DistRoot = Join-Path $RepoRoot "packaging\dist"
$DistExe = Join-Path $DistDir "sentrealm-api.exe"

# Clear stale outputs so upgrades do not keep old sidecars.
if (Test-Path $DistRoot) { Remove-Item -Recurse -Force $DistRoot }
if (Test-Path $WorkDir) { Remove-Item -Recurse -Force $WorkDir }

Write-Host "==> PyInstaller packaging/sentrealm-api.spec (onedir)"
uv run pyinstaller `
    (Join-Path $RepoRoot "packaging\sentrealm-api.spec") `
    --noconfirm `
    --clean `
    --distpath $DistRoot `
    --workpath $WorkDir

if (-not (Test-Path $DistExe)) {
    throw "PyInstaller did not produce: $DistExe"
}

$ResourcesDir = Join-Path $RepoRoot "apps\gui\src-tauri\resources\sentrealm-api"
if (Test-Path $ResourcesDir) { Remove-Item -Recurse -Force $ResourcesDir }
New-Item -ItemType Directory -Force -Path (Split-Path $ResourcesDir) | Out-Null
Copy-Item -Recurse -Force $DistDir $ResourcesDir

# Stale onefile externalBin leftover (pre-onedir layout).
$BinariesDir = Join-Path $RepoRoot "apps\gui\src-tauri\binaries"
Get-ChildItem -Path $BinariesDir -Filter "sentrealm-api-*.exe" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item -Force $_.FullName }

$sizeMb = [math]::Round(((Get-ChildItem $ResourcesDir -Recurse -File | Measure-Object Length -Sum).Sum) / 1MB, 1)
$fileCount = @(Get-ChildItem $ResourcesDir -Recurse -File).Count
Write-Host "==> Sidecar ready (onedir): $ResourcesDir ($sizeMb MB, $fileCount files)"
