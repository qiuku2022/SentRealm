"""Tests for pipeline step 6: LLM send-pool line breaking."""

from __future__ import annotations

import pytest

from sentrealm_core.llm import MockLlmClient
from sentrealm_core.models import Settings
from sentrealm_core.pipeline.flag_lines import flag_overlength_lines
from sentrealm_core.pipeline.line_count import count_line_chars
from sentrealm_core.pipeline.llm_break import iter_llm_break_lines, llm_break_lines


class _FailingLlmClient:
    def break_lines(
        self,
        lines: list[str],
        max_chars: int,
        *,
        min_chars: int | None = None,
    ) -> list[list[str]]:
        raise RuntimeError("boom")


class _AlwaysBadLlmClient:
    def break_lines(
        self,
        lines: list[str],
        max_chars: int,
        *,
        min_chars: int | None = None,
    ) -> list[list[str]]:
        return [[line[:-1] + "X"] for line in lines]


def _configured_settings() -> Settings:
    settings = Settings.defaults()
    settings.llm_enabled = True
    settings.llm_endpoint = "https://example.com/v1"
    settings.llm_model = "test-model"
    settings.min_chars = 2
    return settings


def test_llm_break_skipped_when_not_configured() -> None:
    text = "一二三四五六七八九十十一"
    settings = Settings.defaults()
    assert llm_break_lines(text, max_chars=5, settings=settings) == text


def test_llm_break_uses_mock_client_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    text = "一二三四五六七八九十十一"

    result = llm_break_lines(
        text,
        max_chars=5,
        settings=settings,
        llm_client=MockLlmClient(),
    )

    lines = result.split("\n")
    assert lines == ["一二三四", "五六七八", "九十十一"]
    assert all(count_line_chars(line) <= 5 for line in lines)


def test_llm_break_only_processes_overlength_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    text = "短行\n一二三四五六七八九十十一"

    result = llm_break_lines(
        text,
        max_chars=5,
        settings=settings,
        llm_client=MockLlmClient(),
    )

    lines = result.split("\n")
    assert lines[0] == "短行"
    assert lines[1:] == ["一二三四", "五六七八", "九十十一"]


def test_llm_break_keeps_line_after_three_failed_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    text = "一二三四五六七八九十十一"

    result = llm_break_lines(
        text,
        max_chars=5,
        settings=settings,
        llm_client=_FailingLlmClient(),
    )

    assert result == text


def test_llm_break_abandons_after_three_bad_quality_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    text = "一二三四五六七八九十十一"

    result = llm_break_lines(
        text,
        max_chars=5,
        settings=settings,
        llm_client=_AlwaysBadLlmClient(),
    )

    assert result == text
    assert flag_overlength_lines(result, max_chars=5) == [0]


def test_llm_break_retries_until_quality_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    text = "一二三四五六七八九十十一"
    client = MockLlmClient(bad_results_before_ok=2)

    result = llm_break_lines(
        text,
        max_chars=5,
        settings=settings,
        llm_client=client,
    )

    assert result.split("\n") == ["一二三四", "五六七八", "九十十一"]
    assert len(client.calls) == 3


def test_llm_break_batches_at_most_ten(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    # 11 over-length lines (each 6 chars, max=5)
    lines = [f"超长行{i:02d}字" for i in range(11)]
    # Ensure each is over length 5
    assert all(count_line_chars(line) > 5 for line in lines)
    text = "\n".join(lines)
    client = MockLlmClient()

    llm_break_lines(text, max_chars=5, settings=settings, llm_client=client)

    assert client.calls
    assert all(len(batch) <= 10 for batch in client.calls)
    assert sum(len(batch) for batch in client.calls) >= 11


def test_llm_break_accepts_semantic_segments_above_min_chars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    original = "而如果加上往届未就业的"
    text = f"短\n{original}"

    class _SemanticClient:
        def break_lines(
            self,
            lines: list[str],
            max_chars: int,
            *,
            min_chars: int | None = None,
        ) -> list[list[str]]:
            return [
                ["而如果", "加上往届未就业的"] if line == original else [line]
                for line in lines
            ]

    result = llm_break_lines(
        text,
        max_chars=5,
        settings=settings,
        llm_client=_SemanticClient(),
    )

    assert result.split("\n") == ["短", "而如果", "加上往届未就业的"]


def test_llm_break_rejects_parts_below_configured_min_chars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    settings.min_chars = 4
    original = "发布满打满算才三周时间"

    class _TooFragmentedClient:
        def break_lines(
            self,
            lines: list[str],
            max_chars: int,
            *,
            min_chars: int | None = None,
        ) -> list[list[str]]:
            return [["发布满打", "满算才", "三周时间"] for _line in lines]

    result = llm_break_lines(
        original,
        max_chars=10,
        settings=settings,
        llm_client=_TooFragmentedClient(),
    )

    assert result == original


def test_iter_llm_break_progress_counts_terminal_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    text = "短行\n一二三四五六七八九十十一"

    snapshots = list(
        iter_llm_break_lines(
            text,
            max_chars=5,
            settings=settings,
            llm_client=MockLlmClient(),
        )
    )

    assert snapshots
    _working, llm_current, llm_total = snapshots[-1]
    assert llm_total == 1
    assert llm_current == 1
