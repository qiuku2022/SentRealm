"""SQLite-backed settings store (ADR-004)."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Protocol, runtime_checkable

from sentrealm_core.models import Settings

SCHEMA_VERSION = 2


def migrate_settings_v1_to_v2(data: dict) -> dict:
    """Add break_lexicon from bundled txt when upgrading schema v1."""
    if "break_lexicon" in data:
        return data
    from sentrealm_core.pipeline.break_lexicon import bundled_break_lexicon_settings

    data["break_lexicon"] = bundled_break_lexicon_settings().model_dump(mode="json")
    return data

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS app_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  schema_version INTEGER NOT NULL,
  settings_json TEXT NOT NULL
);
"""


def default_config_path() -> Path:
    """Return the shared SQLite path; ensure parent directory exists."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA is not set")
        path = Path(appdata) / "SentRealm" / "settings.db"
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / "SentRealm" / "settings.db"
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg_config) if xdg_config else Path.home() / ".config"
        path = base / "sentrealm" / "settings.db"

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@runtime_checkable
class SettingsStore(Protocol):
    def load(self) -> Settings: ...

    def save(self, settings: Settings) -> None: ...


class SqliteSettingsStore:
    """Default SettingsStore backed by a single-row SQLite table."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or default_config_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(_CREATE_TABLE_SQL)
        conn.commit()

    def load(self) -> Settings:
        with self._connect() as conn:
            self._ensure_schema(conn)
            row = conn.execute(
                "SELECT schema_version, settings_json FROM app_settings WHERE id = 1"
            ).fetchone()
            if row is None:
                defaults = Settings.defaults()
                self._upsert(conn, defaults)
                return defaults
            stored_version = row["schema_version"]
            if stored_version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"Unsupported settings schema version: {stored_version}"
                )
            data = json.loads(row["settings_json"])
            if stored_version < SCHEMA_VERSION:
                if stored_version == 1:
                    data = migrate_settings_v1_to_v2(data)
                else:
                    raise RuntimeError(
                        f"Unsupported settings schema version: {stored_version}"
                    )
                settings = Settings.model_validate(data)
                self._upsert(conn, settings)
                return settings
            return Settings.model_validate(data)

    def save(self, settings: Settings) -> None:
        normalized = settings.model_copy(deep=True)
        normalized.apply_preset_linkage()
        with self._connect() as conn:
            self._ensure_schema(conn)
            self._upsert(conn, normalized)

    def _upsert(self, conn: sqlite3.Connection, settings: Settings) -> None:
        payload = settings.model_dump(mode="json")
        conn.execute(
            """
            INSERT INTO app_settings (id, schema_version, settings_json)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              schema_version = excluded.schema_version,
              settings_json = excluded.settings_json
            """,
            (SCHEMA_VERSION, json.dumps(payload, ensure_ascii=False)),
        )
        conn.commit()
