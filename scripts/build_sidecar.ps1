# Build PyInstaller FastAPI sidecar and place it for Tauri externalBin (ADR-008).
# Usage (from anywhere):  pwsh -File scripts/build_sidecar.ps1

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

Write-Host "==> uv sync --group packaging"
uv sync --group packaging

$DistExe = Join-Path $RepoRoot "packaging\dist\sentrealm-api.exe"
$WorkDir = Join-Path $RepoRoot "packaging\build"
$DistDir = Join-Path $RepoRoot "packaging\dist"

# Clear stale outputs so upgrades do not keep old sidecars.
if (Test-Path $DistDir) { Remove-Item -Recurse -Force $DistDir }
if (Test-Path $WorkDir) { Remove-Item -Recurse -Force $WorkDir }

Write-Host "==> PyInstaller packaging/sentrealm-api.spec"
uv run pyinstaller `
    (Join-Path $RepoRoot "packaging\sentrealm-api.spec") `
    --noconfirm `
    --clean `
    --distpath $DistDir `
    --workpath $WorkDir

if (-not (Test-Path $DistExe)) {
    throw "PyInstaller did not produce: $DistExe"
}

$TargetTriple = if ($env:TAURI_ENV_TARGET_TRIPLE) {
    $env:TAURI_ENV_TARGET_TRIPLE
} else {
    "x86_64-pc-windows-msvc"
}

$BinariesDir = Join-Path $RepoRoot "apps\gui\src-tauri\binaries"
New-Item -ItemType Directory -Force -Path $BinariesDir | Out-Null

$Dest = Join-Path $BinariesDir "sentrealm-api-$TargetTriple.exe"
Copy-Item -Force $DistExe $Dest

$sizeMb = [math]::Round((Get-Item $Dest).Length / 1MB, 1)
Write-Host "==> Sidecar ready: $Dest ($sizeMb MB)"
