"""Tests for break lexicon loading."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from sentrealm_core.models import BreakLexiconSettings, Settings
from sentrealm_core.pipeline.break_lexicon import (
    BreakLexicon,
    bundled_break_lexicon_settings,
    lexicon_from_settings,
    load_break_lexicon,
    resolve_break_lexicon,
)
from sentrealm_core.store.sqlite import SCHEMA_VERSION, SqliteSettingsStore, migrate_settings_v1_to_v2


def test_load_default_lexicon_contains_product_examples() -> None:
    lexicon = load_break_lexicon()
    assert "重要" in lexicon.protected_words
    assert "非常" in lexicon.break_after_words
    assert "但是" in lexicon.break_after_words
    assert "了" in lexicon.break_after_chars
    assert "吗" in lexicon.break_after_chars
    assert "在" in lexicon.break_before_words
    assert "对于" in lexicon.break_before_words
    assert len(lexicon.break_after_words) >= 20
    assert len(lexicon.break_before_words) >= 15


def test_protected_ranges_detects_internal_split() -> None:
    lexicon = BreakLexicon(protected_words=("重要",))
    line = "这是一个非常重要的技术突破"
    ranges = lexicon.protected_ranges(line)
    assert any(start <= line.index("重") <= end for start, end in ranges)
    assert lexicon.splits_inside_protected(line, line.index("要"))


def test_load_lexicon_from_custom_dir(tmp_path: Path) -> None:
    (tmp_path / "protected_words.txt").write_text("测试\n", encoding="utf-8")
    (tmp_path / "break_after_words.txt").write_text("所以\n", encoding="utf-8")
    (tmp_path / "break_after_chars.txt").write_text("了\n", encoding="utf-8")
    (tmp_path / "break_before_words.txt").write_text("在\n", encoding="utf-8")

    lexicon = load_break_lexicon(tmp_path)
    assert lexicon.protected_words == ("测试",)
    assert lexicon.break_after_words == ("所以",)


def test_bundled_break_lexicon_settings_matches_txt() -> None:
    bundled = load_break_lexicon()
    settings = bundled_break_lexicon_settings()
    assert settings.protected_words == list(bundled.protected_words)
    assert settings.break_after_words == list(bundled.break_after_words)
    assert settings.break_after_chars == sorted(bundled.break_after_chars)
    assert settings.break_before_words == list(bundled.break_before_words)


def test_lexicon_from_settings() -> None:
    settings = BreakLexiconSettings(
        protected_words=["重要"],
        break_after_words=["所以"],
        break_after_chars=["了"],
        break_before_words=["在"],
    )
    lexicon = lexicon_from_settings(settings)
    assert lexicon.protected_words == ("重要",)
    assert lexicon.break_after_chars == frozenset({"了"})


def test_resolve_break_lexicon_uses_settings() -> None:
    settings = Settings.defaults()
    settings.break_lexicon = BreakLexiconSettings(
        protected_words=[],
        break_after_words=[],
        break_after_chars=["测"],
        break_before_words=[],
    )
    lexicon = resolve_break_lexicon(settings)
    assert "测" in lexicon.break_after_chars


def test_resolve_break_lexicon_empty_falls_back_to_bundled() -> None:
    settings = Settings.defaults()
    settings.break_lexicon = BreakLexiconSettings()
    lexicon = resolve_break_lexicon(settings)
    bundled = load_break_lexicon()
    assert lexicon.protected_words == bundled.protected_words


def test_break_lexicon_settings_validation() -> None:
    with pytest.raises(ValidationError):
        BreakLexiconSettings(protected_words=["12345"])

    with pytest.raises(ValidationError):
        BreakLexiconSettings(break_after_chars=["太长"])

    normalized = BreakLexiconSettings(
        protected_words=["重要", "重要", " 就业 "],
        break_after_chars=["了", "了", "的"],
    )
    assert normalized.protected_words == ["重要", "就业"]
    assert normalized.break_after_chars == ["了", "的"]


def test_settings_defaults_include_bundled_lexicon() -> None:
    settings = Settings.defaults()
    assert "重要" in settings.break_lexicon.protected_words


def test_migrate_settings_v1_to_v2_adds_break_lexicon() -> None:
    migrated = migrate_settings_v1_to_v2({"preset": "landscape", "max_chars": 15})
    assert "break_lexicon" in migrated
    assert "重要" in migrated["break_lexicon"]["protected_words"]


def test_sqlite_store_migrates_v1_to_v2(tmp_path: Path) -> None:
    import json
    import sqlite3

    db_path = tmp_path / "settings.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE app_settings (
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
        """,
        (
            json.dumps(
                {
                    "preset": "landscape",
                    "max_chars": 15,
                    "min_chars": 5,
                    "punctuation_remove": [],
                    "punctuation_keep": ["%"],
                    "llm_enabled": False,
                    "llm_endpoint": "",
                    "llm_model": "",
                },
                ensure_ascii=False,
            ),
        ),
    )
    conn.commit()
    conn.close()

    store = SqliteSettingsStore(db_path=db_path)
    settings = store.load()
    assert "重要" in settings.break_lexicon.protected_words

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT schema_version FROM app_settings WHERE id = 1"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == SCHEMA_VERSION
