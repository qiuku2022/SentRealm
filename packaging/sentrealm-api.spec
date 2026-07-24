# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SentRealm FastAPI sidecar (ADR-008).

onedir（目录包）：避免 onefile 每次启动解压到 %TEMP%\\_MEI*，加快冷启动与退出。

Build from repo root:
  uv run pyinstaller packaging/sentrealm-api.spec --noconfirm --clean
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

REPO_ROOT = Path(SPECPATH).resolve().parent
CORE_SRC = REPO_ROOT / "packages" / "core" / "src"
LEXICON_SRC = CORE_SRC / "sentrealm_core" / "data" / "break_lexicon"

block_cipher = None

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "apps.gui.api",
    "apps.gui.api.main",
    "apps.gui.api.routes",
    "apps.gui.api.workspace_routes",
    "apps.gui.api.schemas",
    "apps.gui.api.dependencies",
    "sentrealm_core",
    "sentrealm_core.pipeline",
    "sentrealm_core.pipeline.break_lexicon",
    "sentrealm_core.store",
    "sentrealm_core.env",
    "multipart",
    "email_validator",
]

# Collect pydantic / anyio / starlette submodules that often need hiddenimports.
for pkg in ("pydantic", "pydantic_core", "anyio", "starlette", "fastapi"):
    hiddenimports.extend(collect_submodules(pkg))

# Desktop MVP does not ship cli/mcp (ADR-008).
excludes = [
    "sentrealm_cli",
    "sentrealm_mcp",
    "mcp",
    "typer",
    "tkinter",
    "matplotlib",
    "numpy",
    "pandas",
    "IPython",
    "notebook",
]

datas = [
    (str(LEXICON_SRC), "sentrealm_core/data/break_lexicon"),
]

a = Analysis(
    [str(REPO_ROOT / "packaging" / "sidecar_main.py")],
    pathex=[str(REPO_ROOT), str(CORE_SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="sentrealm-api",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # Windowed subsystem: no console flash when spawned by the GUI (stdio discarded).
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="sentrealm-api",
)
