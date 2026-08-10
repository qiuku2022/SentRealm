"""Tests for LLM configuration helpers and MockLlmClient."""

from __future__ import annotations

import pytest

from sentrealm_core.llm import (
    MockLlmClient,
    _build_batch_user_prompt,
    _parse_batch_break_response,
    check_llm_connection,
    is_llm_configured,
    llm_api_key,
)
from sentrealm_core.models import Settings
from sentrealm_core.pipeline.line_count import count_line_chars
from sentrealm_core.pipeline.llm_quality import llm_quality_ok, quality_ok


def test_llm_api_key_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "  sk-test  ")
    assert llm_api_key() == "sk-test"


def test_is_llm_configured_requires_all_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings.defaults()
    assert is_llm_configured(settings) is False

    settings.llm_enabled = True
    settings.llm_endpoint = "https://example.com/v1"
    settings.llm_model = "test-model"
    assert is_llm_configured(settings) is False

    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    assert is_llm_configured(settings) is True


def test_mock_llm_client_splits_balanced_and_passes_quality() -> None:
    line = "一二三四五六七八九十十一"
    parts = MockLlmClient().break_line(line, max_chars=5)
    assert parts == ["一二三四", "五六七八", "九十十一"]
    assert all(count_line_chars(part) <= 5 for part in parts)
    assert llm_quality_ok(line, parts, min_chars=2)
    assert quality_ok(line, parts, max_chars=5)
    assert "".join(parts) == line


def test_mock_llm_client_break_lines_batch() -> None:
    client = MockLlmClient()
    lines = ["一二三四五六", "甲乙丙丁戊己"]
    result = client.break_lines(lines, max_chars=5)
    assert len(result) == 2
    assert len(client.calls) == 1
    assert client.calls[0] == lines
    assert all(
        llm_quality_ok(src, parts, min_chars=2)
        for src, parts in zip(lines, result)
    )


def test_mock_llm_client_returns_single_line_when_short() -> None:
    line = "短行"
    assert MockLlmClient().break_line(line, max_chars=10) == [line]


def test_llm_prompt_includes_min_chars() -> None:
    prompt = _build_batch_user_prompt(["发布满打满算才三周时间"], 10, min_chars=4)
    assert "最短行长（每行不得少于）：4 字" in prompt


def test_parse_batch_break_response_sections() -> None:
    content = """
### 1
甲乙
丙丁
### 2
一二三
"""
    originals = ["甲乙丙丁", "一二三"]
    parsed = _parse_batch_break_response(content, originals)
    assert parsed == [["甲乙", "丙丁"], ["一二三"]]


def test_parse_batch_break_response_missing_section_falls_back() -> None:
    content = "### 1\n甲\n乙\n"
    originals = ["甲乙", "丙丁"]
    parsed = _parse_batch_break_response(content, originals)
    assert parsed[0] == ["甲", "乙"]
    assert parsed[1] == ["丙丁"]


def test_parse_batch_break_response_headerless_single_item() -> None:
    content = "如果把这群年轻人\n排成一列纵队\n"
    originals = ["如果把这群年轻人排成一列纵队"]
    parsed = _parse_batch_break_response(content, originals)
    assert parsed == [["如果把这群年轻人", "排成一列纵队"]]


def test_parse_batch_break_response_trailing_section_marker() -> None:
    content = "中国高校毕业生\n规模达到了\n1270万人\n人### 1\n"
    originals = ["中国高校毕业生规模达到了1270万人"]
    parsed = _parse_batch_break_response(content, originals)
    assert parsed == [["中国高校毕业生", "规模达到了", "1270万人", "人"]]


def test_check_llm_connection_skipped_when_not_configured() -> None:
    assert check_llm_connection(Settings.defaults()) is None


def test_check_llm_connection_ok_with_mock_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = Settings.defaults()
    settings.llm_enabled = True
    settings.llm_endpoint = "https://example.com/v1"
    settings.llm_model = "test-model"

    assert check_llm_connection(settings, llm_client=MockLlmClient()) is None


def test_check_llm_connection_returns_message_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = Settings.defaults()
    settings.llm_enabled = True
    settings.llm_endpoint = "https://example.com/v1"
    settings.llm_model = "test-model"

    class _FailingClient:
        def ping(self) -> None:
            raise RuntimeError("boom")

    message = check_llm_connection(settings, llm_client=_FailingClient())
    assert message is not None
    assert "boom" in message
