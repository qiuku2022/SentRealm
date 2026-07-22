# Build Windows NSIS installer: sidecar → tauri build (ADR-008).
# Usage:  pwsh -File scripts/build_installer.ps1

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

& (Join-Path $PSScriptRoot "build_sidecar.ps1")

Write-Host "==> pnpm install (gui)"
Push-Location (Join-Path $RepoRoot "apps\gui")
try {
    pnpm install
    Write-Host "==> pnpm build (tauri build → NSIS)"
    pnpm build
} finally {
    Pop-Location
}

$BundleDir = if ($env:CARGO_TARGET_DIR) {
    Join-Path $env:CARGO_TARGET_DIR "release\bundle\nsis"
} else {
    Join-Path $RepoRoot "apps\gui\src-tauri\target\release\bundle\nsis"
}

# Also mirror into the conventional path for easier discovery.
$MirrorDir = Join-Path $RepoRoot "apps\gui\src-tauri\target\release\bundle\nsis"
Write-Host "==> Done. Look for installer under:"
Write-Host "    $BundleDir"
if (Test-Path $BundleDir) {
    Get-ChildItem $BundleDir -Filter "*.exe" | ForEach-Object {
        $mb = [math]::Round($_.Length / 1MB, 1)
        Write-Host ("    - {0} ({1} MB)" -f $_.FullName, $mb)
        if ($BundleDir -ne $MirrorDir) {
            New-Item -ItemType Directory -Force -Path $MirrorDir | Out-Null
            Copy-Item -Force $_.FullName $MirrorDir
            Write-Host ("    mirrored → {0}" -f (Join-Path $MirrorDir $_.Name))
        }
    }
}
