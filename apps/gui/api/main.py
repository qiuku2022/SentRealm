"""FastAPI application entrypoint for gui (ADR-006: apps.gui.api.main:app)."""



from __future__ import annotations



import os



from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware



from sentrealm_core.env import load_project_env

from sentrealm_core.store import SettingsStore, SqliteSettingsStore, WorkspaceStore



from apps.gui.api.routes import router, settings_router

from apps.gui.api.workspace_routes import workspace_router



# Local HTTP API is only bound to 127.0.0.1; CORS must allow both Vite (dev)
# and Tauri 2 custom-protocol origins (production WebView), or fetch(/health)
# fails silently in the installed app.
_CORS_ORIGINS = [
    "http://localhost:1420",
    "http://127.0.0.1:1420",
    "https://tauri.localhost",
    "http://tauri.localhost",
    "tauri://localhost",
    "https://asset.localhost",
    "http://asset.localhost",
]


def _cors_enabled() -> bool:
    value = os.getenv("SENTREALM_ENABLE_CORS", "1").strip().lower()
    return value not in ("0", "false", "no", "off")


def create_app(
    store: SettingsStore | None = None,
    workspace_store: WorkspaceStore | None = None,
) -> FastAPI:
    load_project_env()

    app = FastAPI(title="SentRealm GUI API", version="1.0.0")
    app.state.store = store or SqliteSettingsStore()
    app.state.workspace_store = workspace_store or WorkspaceStore()

    if _cors_enabled():
        app.add_middleware(
            CORSMiddleware,
            allow_origins=_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )



    app.include_router(router)

    app.include_router(settings_router)

    app.include_router(workspace_router)

    return app





app = create_app()

