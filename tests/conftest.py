"""Shared pytest fixtures for cross-entry tests."""



from __future__ import annotations



from pathlib import Path



import pytest

from fastapi.testclient import TestClient

from typer.testing import CliRunner



from apps.gui.api.main import create_app

from sentrealm_core import SqliteSettingsStore

from sentrealm_core.store import WorkspaceStore





@pytest.fixture(autouse=True)

def _clear_llm_api_key_from_local_env(monkeypatch: pytest.MonkeyPatch) -> None:

    """`.env` may be loaded by API create_app(); keep unit tests hermetic."""

    monkeypatch.delenv("SENTREALM_LLM_API_KEY", raising=False)





@pytest.fixture

def shared_store(tmp_path: Path) -> SqliteSettingsStore:

    return SqliteSettingsStore(db_path=tmp_path / "settings.db")





@pytest.fixture

def workspace_store(tmp_path: Path) -> WorkspaceStore:

    return WorkspaceStore(root=tmp_path / "workspace")





@pytest.fixture

def api_client(shared_store: SqliteSettingsStore, workspace_store: WorkspaceStore) -> TestClient:

    return TestClient(create_app(store=shared_store, workspace_store=workspace_store))





@pytest.fixture

def cli_runner(

    shared_store: SqliteSettingsStore, monkeypatch: pytest.MonkeyPatch

) -> CliRunner:

    monkeypatch.setattr("sentrealm_cli.main.get_store", lambda: shared_store)

    monkeypatch.setattr("sentrealm_mcp.main.get_store", lambda: shared_store)

    return CliRunner()

