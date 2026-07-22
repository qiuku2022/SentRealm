"""FastAPI dependencies for the gui API layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from sentrealm_core.store import SettingsStore, WorkspaceStore


def get_store(request: Request) -> SettingsStore:
    return request.app.state.store


def get_workspace_store(request: Request) -> WorkspaceStore:
    return request.app.state.workspace_store


StoreDep = Annotated[SettingsStore, Depends(get_store)]
WorkspaceDep = Annotated[WorkspaceStore, Depends(get_workspace_store)]
