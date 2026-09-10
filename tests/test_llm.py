"""Tests for LLM configuration helpers and MockLlmClient."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from sentrealm_core.llm import (
    OUTCOME_EMPTY,
    OUTCOME_PARSED,
    OUTCOME_TRUNCATED,
    LineBreakResult,
    MockLlmClient,
    OpenAILlmClient,
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
    result = MockLlmClient().break_line(line, max_chars=5)
    parts = result.parts
    assert result.outcome == OUTCOME_PARSED
    assert parts == ["一二三四", "五六七八", "九十十一"]
    assert all(count_line_chars(part) <= 5 for part in parts)
    assert llm_quality_ok(line, parts)
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
        llm_quality_ok(src, item.parts) for src, item in zip(lines, result, strict=True)
    )


def test_mock_llm_client_returns_single_line_when_short() -> None:
    line = "短行"
    result = MockLlmClient().break_line(line, max_chars=10)
    assert result.parts == [line]
    assert result.outcome == OUTCOME_PARSED


def test_llm_prompt_includes_min_chars() -> None:
    prompt = _build_batch_user_prompt(["发布满打满算才三周时间"], 10, min_chars=4)
    assert "建议最短行长：不少于 4 字；禁止单字成行" in prompt
    assert "硬性目标：每行不超过 10 字" in prompt
    assert "能在语义边界切开则必须切开" in prompt


def test_llm_system_prompt_forbids_overlength_and_single_char() -> None:
    from sentrealm_core.llm import _SYSTEM_PROMPT

    assert "必须 ≤ N" in _SYSTEM_PROMPT or "必须≤N" in _SYSTEM_PROMPT.replace(" ", "")
    assert "禁止" in _SYSTEM_PROMPT and "单字" in _SYSTEM_PROMPT
    assert "可略超" not in _SYSTEM_PROMPT or "找不到合理切点" in _SYSTEM_PROMPT


def test_llm_prompt_includes_wave2_note() -> None:
    prompt = _build_batch_user_prompt(
        ["可KK园区拆平不到半年"],
        10,
        min_chars=5,
        wave=2,
        retry_hint="长度返工：请重新切分整句",
    )
    assert "本条为长度返工（第 2 波）" in prompt
    assert "返工说明：长度返工" in prompt


def test_llm_prompt_includes_retry_hint() -> None:
    prompt = _build_batch_user_prompt(
        ["发布满打满算才三周时间"],
        10,
        min_chars=4,
        retry_hint="上次未形成多行，请在语义边界插入换行",
    )
    assert "返工说明：上次未形成多行，请在语义边界插入换行" in prompt
    assert "sk-" not in prompt


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


def test_parse_batch_break_response_missing_section_is_empty() -> None:
    content = "### 1\n甲\n乙\n"
    originals = ["甲乙", "丙丁"]
    parsed = _parse_batch_break_response(content, originals)
    assert parsed[0] == ["甲", "乙"]
    assert parsed[1] == []


def test_parse_batch_break_response_empty_content() -> None:
    assert _parse_batch_break_response("", ["原文一行"]) == [[]]
    assert _parse_batch_break_response("   \n  ", ["原文一行"]) == [[]]


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


def test_openai_empty_content_outcome() -> None:
    client = OpenAILlmClient(
        endpoint="https://example.com/v1",
        model="test",
        api_key="sk-test",
    )

    class _FakeCompletions:
        def create(self, **_kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=""),
                        finish_reason="stop",
                    )
                ]
            )

    fake = SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions()))
    result = client._break_one_line(fake, "一二三四五六七八九十", max_chars=5)
    assert result.outcome == OUTCOME_EMPTY
    assert result.parts == []


def test_openai_truncation_retries_then_marks_truncated() -> None:
    client = OpenAILlmClient(
        endpoint="https://example.com/v1",
        model="test",
        api_key="sk-test",
    )
    calls: list[int] = []

    class _FakeCompletions:
        def create(self, **kwargs: object) -> SimpleNamespace:
            max_tokens = int(kwargs["max_tokens"])  # type: ignore[index]
            calls.append(max_tokens)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="一二\n三四"),
                        finish_reason="length",
                    )
                ]
            )

    fake = SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions()))
    result = client._break_one_line(fake, "一二三四五六七八九十", max_chars=5)
    assert len(calls) == 2
    assert calls[1] > calls[0]
    assert result.outcome == OUTCOME_TRUNCATED
    assert result.finish_reason == "length"
    assert result.parts == ["一二", "三四"]


def test_openai_isolates_line_failures_and_fail_fast_config() -> None:
    client = OpenAILlmClient(
        endpoint="https://example.com/v1",
        model="test",
        api_key="sk-test",
    )
    calls = 0

    class _AuthError(Exception):
        status_code = 401

    class _FakeCompletions:
        def create(self, **_kwargs: object) -> SimpleNamespace:
            nonlocal calls
            calls += 1
            if calls == 1:
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content="甲乙\n丙丁戊己"),
                            finish_reason="stop",
                        )
                    ]
                )
            raise _AuthError("unauthorized")

    fake = SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions()))
    results: list[LineBreakResult] = []
    config_status: int | None = None
    lines = ["甲乙丙丁戊己", "超长行乙一二三四", "超长行丙一二三四"]
    for line in lines:
        if config_status is not None:
            results.append(
                LineBreakResult(
                    parts=[], outcome="config_error", http_status=config_status
                )
            )
            continue
        item = client._break_one_line(fake, line, max_chars=5)
        results.append(item)
        if item.outcome == "config_error":
            config_status = item.http_status

    assert results[0].outcome == OUTCOME_PARSED
    assert results[0].parts == ["甲乙", "丙丁戊己"]
    assert results[1].outcome == "config_error"
    assert results[2].outcome == "config_error"
    assert calls == 2  # third line skipped after config error


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
