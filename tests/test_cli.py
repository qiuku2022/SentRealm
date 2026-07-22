"""Tests for sentrealm CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sentrealm_cli.main import app, get_store
from sentrealm_core import SqliteSettingsStore


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cli_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SqliteSettingsStore:
    store = SqliteSettingsStore(db_path=tmp_path / "settings.db")
    monkeypatch.setattr("sentrealm_cli.main.get_store", lambda: store)
    return store


def test_preprocess_help(runner: CliRunner) -> None:
    result = runner.invoke(app, ["preprocess", "--help"])

    assert result.exit_code == 0
    assert "--stdin" in result.stdout
    assert "--preset" in result.stdout
    assert "--max-chars" in result.stdout


def test_preprocess_requires_input_source(runner: CliRunner, cli_store: SqliteSettingsStore) -> None:
    del cli_store
    result = runner.invoke(app, ["preprocess"])

    assert result.exit_code == 1


def test_preprocess_rejects_both_input_and_stdin(
    runner: CliRunner, cli_store: SqliteSettingsStore, tmp_path: Path
) -> None:
    del cli_store
    input_file = tmp_path / "draft.txt"
    input_file.write_text("hello", encoding="utf-8")

    result = runner.invoke(app, ["preprocess", "-i", str(input_file), "--stdin"])

    assert result.exit_code == 1


def test_preprocess_stdin_success(runner: CliRunner, cli_store: SqliteSettingsStore) -> None:
    del cli_store
    result = runner.invoke(app, ["preprocess", "--stdin"], input="第一行\n第二行")

    assert result.exit_code == 0
    assert result.stdout == "第一行\n第二行"
    meta = json.loads(result.stderr.strip())
    assert meta == {"line_count": 2, "flagged_lines": []}


def test_preprocess_stdin_empty_exits_1(runner: CliRunner, cli_store: SqliteSettingsStore) -> None:
    del cli_store
    result = runner.invoke(app, ["preprocess", "--stdin"], input="   ")

    assert result.exit_code == 1


def test_preprocess_input_file_and_output(
    runner: CliRunner, cli_store: SqliteSettingsStore, tmp_path: Path
) -> None:
    del cli_store
    input_file = tmp_path / "draft.txt"
    output_file = tmp_path / "out.txt"
    input_file.write_text("hello", encoding="utf-8")

    result = runner.invoke(
        app,
        ["preprocess", "-i", str(input_file), "-o", str(output_file), "--preset", "portrait"],
    )

    assert result.exit_code == 0
    assert output_file.read_text(encoding="utf-8") == "hello"
    assert json.loads(result.stderr.strip()) == {"line_count": 1, "flagged_lines": []}


def test_preprocess_missing_input_file_exits_1(
    runner: CliRunner, cli_store: SqliteSettingsStore, tmp_path: Path
) -> None:
    del cli_store
    missing = tmp_path / "missing.txt"

    result = runner.invoke(app, ["preprocess", "-i", str(missing)])

    assert result.exit_code == 1
