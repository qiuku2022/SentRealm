"""Tests for sentrealm MCP server."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentrealm_core import apply_runtime_overrides
from sentrealm_core.models import Settings
from sentrealm_mcp.main import mcp, preprocess_text


@pytest.fixture
def mcp_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from sentrealm_core import SqliteSettingsStore

    store = SqliteSettingsStore(db_path=tmp_path / "settings.db")
    monkeypatch.setattr("sentrealm_mcp.main.get_store", lambda: store)
    return store


def test_preprocess_text_returns_preprocess_response_shape(mcp_store) -> None:
    del mcp_store
    result = preprocess_text("第一行\n第二行")

    assert result == {
        "original": "第一行\n第二行",
        "processed": "第一行\n第二行",
        "line_count": 2,
        "flagged_lines": [],
    }


def test_preprocess_text_rejects_blank_input(mcp_store) -> None:
    del mcp_store
    with pytest.raises(ValueError, match="empty or whitespace-only"):
        preprocess_text("   ")


def test_preprocess_text_applies_max_chars_override(mcp_store) -> None:
    del mcp_store
    result = preprocess_text("hello", max_chars=20)

    assert result["processed"] == "hello"
    assert result["line_count"] == 1


def test_mcp_registers_preprocess_text_tool() -> None:
    tools = mcp._tool_manager.list_tools()
    names = {tool.name for tool in tools}

    assert names == {"preprocess_text"}


def test_apply_runtime_overrides_preset_then_max_chars() -> None:
    base = Settings.defaults()
    merged = apply_runtime_overrides(base, preset="portrait", max_chars=20)

    assert merged.preset == "custom"
    assert merged.max_chars == 20
