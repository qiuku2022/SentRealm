"""Production FastAPI entry for PyInstaller sidecar (ADR-008)."""

from __future__ import annotations

import uvicorn

# Production WebView origin is https://tauri.localhost — keep CORS enabled
# (see apps.gui.api.main._CORS_ORIGINS). Do not set SENTREALM_ENABLE_CORS=0.

from apps.gui.api.main import app  # noqa: E402


def main() -> None:
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=17300,
        # PyInstaller windowed mode has no sys.stdout/sys.stderr. Uvicorn's
        # default logging config binds both streams and otherwise fails before
        # the socket starts listening. Tauri discards sidecar stdio anyway.
        log_config=None,
        access_log=False,
        # No reload in production sidecar.
        reload=False,
    )


if __name__ == "__main__":
    main()
