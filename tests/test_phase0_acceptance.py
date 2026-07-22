"""Phase 0 §6 acceptance — cross-entry boundaries and shared SQLite."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from sentrealm_cli.main import app as cli_app
from sentrealm_mcp.main import preprocess_text


def test_api_put_settings_visible_to_cli(
    api_client: TestClient, cli_runner: CliRunner, shared_store: SqliteSettingsStore
) -> None:
    """HTTP PUT /settings and CLI preprocess must share the same SQLite file."""
    del shared_store
    payload = api_client.get("/api/v1/settings").json()
    payload["preset"] = "portrait"
    payload["max_chars"] = 99

    put = api_client.put("/api/v1/settings", json=payload)
    assert put.status_code == 200
    assert put.json()["preset"] == "portrait"
    assert put.json()["max_chars"] == 10

    result = cli_runner.invoke(cli_app, ["preprocess", "--stdin"], input="hello")
    assert result.exit_code == 0
    meta = json.loads(result.stderr.strip())
    assert meta["line_count"] == 1


def test_api_put_settings_visible_to_mcp(
    api_client: TestClient, shared_store: SqliteSettingsStore
) -> None:
    del shared_store
    payload = api_client.get("/api/v1/settings").json()
    payload["preset"] = "landscape"
    payload["max_chars"] = 15

    assert api_client.put("/api/v1/settings", json=payload).status_code == 200

    result = preprocess_text("line one\nline two")
    assert result["line_count"] == 2
    assert set(result) == {"original", "processed", "line_count", "flagged_lines"}


def test_preprocess_field_contract_http(api_client: TestClient) -> None:
    response = api_client.post("/api/v1/preprocess", json={"text": "a\nb"})
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"original", "processed", "line_count", "flagged_lines"}


def test_preprocess_field_contract_cli(cli_runner: CliRunner, shared_store: SqliteSettingsStore) -> None:
    del shared_store
    result = cli_runner.invoke(cli_app, ["preprocess", "--stdin"], input="a\nb")
    assert result.exit_code == 0
    meta = json.loads(result.stderr.strip())
    assert set(meta) == {"line_count", "flagged_lines"}


def test_preprocess_field_contract_mcp(shared_store: SqliteSettingsStore) -> None:
    del shared_store
    result = preprocess_text("a\nb")
    assert set(result) == {"original", "processed", "line_count", "flagged_lines"}
