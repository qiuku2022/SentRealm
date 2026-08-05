"""Tests for apps/gui/api FastAPI thin layer."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sentrealm_core import Settings, SqliteSettingsStore
from sentrealm_core.models import DEFAULT_PUNCTUATION_KEEP, DEFAULT_PUNCTUATION_REMOVE

from apps.gui.api.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    store = SqliteSettingsStore(db_path=tmp_path / "settings.db")
    app = create_app(store=store)
    return TestClient(app)


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_cors_allows_tauri_production_origin(client: TestClient) -> None:
    """Installed WebView origin must be allowed (otherwise UI stuck on connecting)."""
    response = client.options(
        "/health",
        headers={
            "Origin": "https://tauri.localhost",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://tauri.localhost"

    get_response = client.get(
        "/health",
        headers={"Origin": "https://tauri.localhost"},
    )
    assert get_response.status_code == 200
    assert get_response.headers.get("access-control-allow-origin") == "https://tauri.localhost"


def test_get_settings_returns_defaults(client: TestClient) -> None:
    response = client.get("/api/v1/settings")

    assert response.status_code == 200
    data = response.json()
    assert data["preset"] == "landscape"
    assert data["max_chars"] == 15
    assert data["min_chars"] == 5
    assert data["punctuation_remove"] == DEFAULT_PUNCTUATION_REMOVE
    assert data["punctuation_keep"] == DEFAULT_PUNCTUATION_KEEP
    assert data["llm_enabled"] is False
    assert data["llm_endpoint"] == ""
    assert data["llm_model"] == ""
    assert "重要" in data["break_lexicon"]["protected_words"]
    assert "了" in data["break_lexicon"]["break_after_chars"]


def test_get_break_lexicon_defaults(client: TestClient) -> None:
    response = client.get("/api/v1/break-lexicon/defaults")

    assert response.status_code == 200
    data = response.json()
    assert "重要" in data["protected_words"]
    assert "非常" not in data["break_after_words"]
    assert "了" in data["break_after_chars"]
    assert "在" in data["break_before_words"]


def test_put_settings_rejects_invalid_break_lexicon(client: TestClient) -> None:
    payload = client.get("/api/v1/settings").json()
    payload["break_lexicon"]["break_after_chars"] = ["太长"]

    response = client.put("/api/v1/settings", json=payload)

    assert response.status_code == 422


def test_put_settings_break_lexicon_round_trip(client: TestClient) -> None:
    payload = client.get("/api/v1/settings").json()
    payload["break_lexicon"]["break_after_chars"] = ["测", "试"]

    response = client.put("/api/v1/settings", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["break_lexicon"]["break_after_chars"] == ["测", "试"]


def test_get_llm_key_status(client: TestClient) -> None:
    response = client.get("/api/v1/settings/llm-key-status")

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"configured"}
    assert isinstance(data["configured"], bool)


def test_post_llm_test_skipped_when_not_configured(client: TestClient) -> None:
    response = client.post("/api/v1/settings/llm-test")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "skipped": True, "message": None}


def test_post_llm_test_ok_with_mock(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    payload = client.get("/api/v1/settings").json()
    payload["llm_enabled"] = True
    payload["llm_endpoint"] = "https://example.com/v1"
    payload["llm_model"] = "test-model"
    client.put("/api/v1/settings", json=payload)

    monkeypatch.setattr(
        "apps.gui.api.routes.check_llm_connection",
        lambda settings: None,
    )

    response = client.post("/api/v1/settings/llm-test")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "skipped": False, "message": None}


def test_post_llm_test_failure_returns_message(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    payload = client.get("/api/v1/settings").json()
    payload["llm_enabled"] = True
    payload["llm_endpoint"] = "https://example.com/v1"
    payload["llm_model"] = "test-model"
    client.put("/api/v1/settings", json=payload)

    monkeypatch.setattr(
        "apps.gui.api.routes.check_llm_connection",
        lambda settings: "无法连接 LLM 端点",
    )

    response = client.post("/api/v1/settings/llm-test")

    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "skipped": False,
        "message": "无法连接 LLM 端点",
    }


def test_put_settings_round_trip_and_preset_linkage(client: TestClient) -> None:
    payload = client.get("/api/v1/settings").json()
    payload["preset"] = "portrait"
    payload["max_chars"] = 99
    payload["llm_enabled"] = True
    payload["llm_endpoint"] = "https://example.com/v1"
    payload["llm_model"] = "test-model"

    response = client.put("/api/v1/settings", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["preset"] == "portrait"
    assert data["max_chars"] == 10
    assert data["llm_enabled"] is True
    assert data["llm_endpoint"] == "https://example.com/v1"
    assert data["llm_model"] == "test-model"


def test_put_settings_rejects_invalid_custom_max_chars(client: TestClient) -> None:
    payload = client.get("/api/v1/settings").json()
    payload["preset"] = "custom"
    payload["max_chars"] = 0

    response = client.put("/api/v1/settings", json=payload)

    assert response.status_code == 422


def test_post_preprocess_uses_store_settings(client: TestClient) -> None:
    response = client.post(
        "/api/v1/preprocess",
        json={"text": "第一行\n第二行", "settings": None},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["original"] == "第一行\n第二行"
    assert data["processed"] == "第一行\n第二行"
    assert data["line_count"] == 2
    assert data["flagged_lines"] == []


def test_post_preprocess_accepts_request_settings_override(client: TestClient) -> None:
    settings = Settings.defaults().model_dump()
    settings["preset"] = "custom"
    settings["max_chars"] = 20

    response = client.post(
        "/api/v1/preprocess",
        json={"text": "hello", "settings": settings},
    )

    assert response.status_code == 200
    assert response.json()["processed"] == "hello"


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_post_preprocess_rejects_empty_text(client: TestClient, text: str) -> None:
    response = client.post("/api/v1/preprocess", json={"text": text})

    assert response.status_code == 400
    assert response.json() == {"detail": "文稿不能为空"}


def test_post_preprocess_stream_emits_progress_and_done(client: TestClient) -> None:
    response = client.post(
        "/api/v1/preprocess/stream",
        json={"text": "第一行\n第二行"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert '"type": "progress"' in body
    assert '"phase": "rules"' in body
    assert '"type": "done"' in body
    assert "第一行" in body


def test_post_preprocess_stream_rejects_empty_text(client: TestClient) -> None:
    response = client.post("/api/v1/preprocess/stream", json={"text": "   "})

    assert response.status_code == 400
    assert response.json() == {"detail": "文稿不能为空"}
