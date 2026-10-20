"""Phase 0 §6 acceptance — cross-entry boundaries and shared SQLite."""

from __future__ import annotations

from fastapi.testclient import TestClient

from sentrealm_core import SqliteSettingsStore
from sentrealm_mcp.main import preprocess_text


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


def test_preprocess_field_contract_mcp(shared_store: SqliteSettingsStore) -> None:
    del shared_store
    result = preprocess_text("a\nb")
    assert set(result) == {"original", "processed", "line_count", "flagged_lines"}
