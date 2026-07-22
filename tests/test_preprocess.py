"""Tests for full preprocess orchestration."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from sentrealm_core import MockLlmClient, Settings, iter_preprocess, preprocess
from sentrealm_core.models import BreakLexiconSettings, PreprocessProgress, PreprocessResult
from sentrealm_core.pipeline import EmptyTextError
from sentrealm_cli.main import app as cli_app
from sentrealm_mcp.main import preprocess_text


def test_preprocess_golden_sample_punctuation_and_whitespace() -> None:
    text = "大家好，欢迎来到今天的节目。今天我们聊聊 AI 技术。"
    result = preprocess(text, Settings.defaults())

    assert result.original == text
    assert result.processed.split("\n") == [
        "大家好",
        "欢迎来到今天的节目",
        "今天我们聊聊 AI 技术",
    ]
    assert result.line_count == 3
    assert result.flagged_lines == []


def test_preprocess_flags_line_when_rule_break_cannot_split() -> None:
    text = "abcdefghijklmnopqrstuvwxyz"
    settings = Settings.defaults()
    settings.max_chars = 5
    settings.min_chars = 2

    result = preprocess(text, settings)

    assert result.processed == text
    assert result.line_count == 1
    assert result.flagged_lines == [0]


def test_preprocess_mock_llm_breaks_overlength_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = Settings.defaults()
    settings.llm_enabled = True
    settings.llm_endpoint = "https://example.com/v1"
    settings.llm_model = "test-model"
    settings.max_chars = 5
    settings.min_chars = 2
    text = "一二三四五六七八九十十一"

    result = preprocess(text, settings, llm_client=MockLlmClient())

    assert result.flagged_lines == []
    assert result.processed.split("\n") == ["一二三四", "五六七八", "九十十一"]
    assert result.line_count == 3


def test_preprocess_uses_settings_break_lexicon() -> None:
    settings = Settings.defaults()
    settings.max_chars = 10
    settings.min_chars = 2
    settings.break_lexicon = BreakLexiconSettings(
        protected_words=[],
        break_after_words=[],
        break_after_chars=["五"],
        break_before_words=[],
    )
    text = "一二三四五六七八九十十一"

    result = preprocess(text, settings)

    assert result.processed.split("\n") == ["一二三四五", "六七八九十十一"]
    assert result.flagged_lines == []


def test_preprocess_short_multiline_unchanged() -> None:
    settings = Settings.defaults()
    text = "第一行\n第二行"

    result = preprocess(text, settings)

    assert result.processed == text
    assert result.line_count == 2
    assert result.flagged_lines == []


def test_preprocess_ignores_injected_llm_client_when_llm_not_configured() -> None:
    settings = Settings.defaults()
    settings.max_chars = 5
    settings.min_chars = 2
    text = "一二三四五六七八九十十一"

    result = preprocess(text, settings, llm_client=MockLlmClient())

    assert result.flagged_lines == [0]
    assert result.processed == text


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_preprocess_rejects_empty_text(text: str) -> None:
    with pytest.raises(EmptyTextError):
        preprocess(text, Settings.defaults())


def test_multi_entry_preprocess_consistency(
    api_client: TestClient,
    cli_runner: CliRunner,
    shared_store,
) -> None:
    del shared_store
    text = "大家好，欢迎来到今天的节目。今天我们聊聊 AI 技术。"
    settings = Settings.defaults()

    direct = preprocess(text, settings)
    http = api_client.post("/api/v1/preprocess", json={"text": text}).json()
    cli = cli_runner.invoke(cli_app, ["preprocess", "--stdin"], input=text)
    mcp = preprocess_text(text)

    assert cli.exit_code == 0
    cli_meta = json.loads(cli.stderr.strip())

    assert http["processed"] == direct.processed == cli.stdout == mcp["processed"]
    assert http["line_count"] == direct.line_count == cli_meta["line_count"] == mcp["line_count"]
    assert (
        http["flagged_lines"]
        == direct.flagged_lines
        == cli_meta["flagged_lines"]
        == mcp["flagged_lines"]
    )


def test_iter_preprocess_yields_rules_then_result() -> None:
    text = "第一行\n第二行"
    events = list(iter_preprocess(text, Settings.defaults()))

    assert len(events) == 2
    assert isinstance(events[0], PreprocessProgress)
    assert events[0].phase == "rules"
    assert isinstance(events[-1], PreprocessResult)
    assert events[-1].processed == text


def test_iter_preprocess_yields_llm_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = Settings.defaults()
    settings.llm_enabled = True
    settings.llm_endpoint = "https://example.com/v1"
    settings.llm_model = "test-model"
    settings.max_chars = 5
    settings.min_chars = 2
    text = "短行\n一二三四五六七八九十十一"

    events = list(
        iter_preprocess(text, settings, llm_client=MockLlmClient()),
    )

    assert any(
        isinstance(event, PreprocessProgress) and event.phase == "llm"
        for event in events
    )
    assert isinstance(events[-1], PreprocessResult)
    assert events[-1].flagged_lines == []
