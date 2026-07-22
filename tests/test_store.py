"""Tests for SettingsStore and default configuration path."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from sentrealm_core import Settings, SqliteSettingsStore, default_config_path
from sentrealm_core.models import DEFAULT_PUNCTUATION_KEEP, DEFAULT_PUNCTUATION_REMOVE


@pytest.fixture
def store(tmp_path: Path) -> SqliteSettingsStore:
    return SqliteSettingsStore(db_path=tmp_path / "settings.db")


def test_load_returns_defaults_on_first_access(store: SqliteSettingsStore) -> None:
    settings = store.load()

    assert settings.preset == "landscape"
    assert settings.max_chars == 15
    assert settings.punctuation_remove == DEFAULT_PUNCTUATION_REMOVE
    assert settings.punctuation_keep == DEFAULT_PUNCTUATION_KEEP
    assert settings.min_chars == 5
    assert settings.llm_enabled is False
    assert settings.llm_endpoint == ""
    assert settings.llm_model == ""


def test_save_and_load_round_trip(store: SqliteSettingsStore) -> None:
    original = store.load()
    original.llm_enabled = True
    original.llm_endpoint = "https://example.com/v1"
    original.llm_model = "test-model"
    store.save(original)

    loaded = store.load()
    assert loaded.llm_enabled is True
    assert loaded.llm_endpoint == "https://example.com/v1"
    assert loaded.llm_model == "test-model"


def test_save_applies_landscape_preset_linkage(store: SqliteSettingsStore) -> None:
    settings = store.load()
    settings.preset = "landscape"
    settings.max_chars = 99
    store.save(settings)

    loaded = store.load()
    assert loaded.preset == "landscape"
    assert loaded.max_chars == 15


def test_save_applies_portrait_preset_linkage(store: SqliteSettingsStore) -> None:
    settings = store.load()
    settings.preset = "portrait"
    settings.max_chars = 99
    store.save(settings)

    loaded = store.load()
    assert loaded.preset == "portrait"
    assert loaded.max_chars == 10


def test_save_preserves_custom_max_chars(store: SqliteSettingsStore) -> None:
    settings = store.load()
    settings.preset = "custom"
    settings.max_chars = 20
    settings.min_chars = 6
    store.save(settings)

    loaded = store.load()
    assert loaded.preset == "custom"
    assert loaded.max_chars == 20
    assert loaded.min_chars == 6


def test_load_fills_default_min_chars_for_legacy_json(store: SqliteSettingsStore) -> None:
    """Old DB rows without min_chars still load with DEFAULT_MIN_CHARS."""
    import json
    import sqlite3

    legacy = {
        "preset": "landscape",
        "max_chars": 15,
        "punctuation_remove": [],
        "punctuation_keep": ["%"],
        "llm_enabled": False,
        "llm_endpoint": "",
        "llm_model": "",
    }
    with sqlite3.connect(store.db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
              id INTEGER PRIMARY KEY CHECK (id = 1),
              schema_version INTEGER NOT NULL,
              settings_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO app_settings (id, schema_version, settings_json)
            VALUES (1, 1, ?)
            ON CONFLICT(id) DO UPDATE SET settings_json = excluded.settings_json
            """,
            (json.dumps(legacy),),
        )
        conn.commit()

    loaded = store.load()
    assert loaded.min_chars == 5


@pytest.mark.skipif(sys.platform != "win32", reason="Windows path is the Phase 0 target")
def test_default_config_path_on_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    appdata = tmp_path / "Roaming"
    monkeypatch.setenv("APPDATA", str(appdata))

    path = default_config_path()

    assert path == appdata / "SentRealm" / "settings.db"
    assert path.parent.is_dir()
    assert os.access(path.parent, os.W_OK)

