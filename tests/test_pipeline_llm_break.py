"""Tests for pipeline step 6: LLM send-pool line breaking."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from sentrealm_core.llm import (
    OUTCOME_CONFIG_ERROR,
    OUTCOME_EMPTY,
    OUTCOME_PARSED,
    OUTCOME_REQUEST_ERROR,
    LineBreakResult,
    MockLlmClient,
    parsed_line_break,
)
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
        retry_hints: Sequence[str | None] | None = None,
    ) -> list[LineBreakResult]:
        raise RuntimeError("boom")


class _AlwaysBadLlmClient:
    def break_lines(
        self,
        lines: list[str],
        max_chars: int,
        *,
        min_chars: int | None = None,
        retry_hints: Sequence[str | None] | None = None,
    ) -> list[LineBreakResult]:
        return [parsed_line_break([line[:-1] + "X"]) for line in lines]


class _EmptyThenOkClient:
    def __init__(self) -> None:
        self.calls = 0
        self.hints: list[list[str | None] | None] = []

    def break_lines(
        self,
        lines: list[str],
        max_chars: int,
        *,
        min_chars: int | None = None,
        retry_hints: Sequence[str | None] | None = None,
    ) -> list[LineBreakResult]:
        self.calls += 1
        self.hints.append(list(retry_hints) if retry_hints is not None else None)
        if self.calls == 1:
            return [
                LineBreakResult(parts=[], outcome=OUTCOME_EMPTY) for _line in lines
            ]
        return [
            parsed_line_break(["一二三四", "五六七八", "九十十一"]) for _line in lines
        ]


class _ConfigErrorClient:
    calls = 0

    def break_lines(
        self,
        lines: list[str],
        max_chars: int,
        *,
        min_chars: int | None = None,
        retry_hints: Sequence[str | None] | None = None,
    ) -> list[LineBreakResult]:
        type(self).calls += 1
        return [
            LineBreakResult(parts=[], outcome=OUTCOME_CONFIG_ERROR, http_status=401)
            for _line in lines
        ]


class _PartialBatchClient:
    """First line OK; second line request error — isolation must keep first."""

    def break_lines(
        self,
        lines: list[str],
        max_chars: int,
        *,
        min_chars: int | None = None,
        retry_hints: Sequence[str | None] | None = None,
    ) -> list[LineBreakResult]:
        results: list[LineBreakResult] = []
        for line in lines:
            if line.startswith("甲"):
                results.append(parsed_line_break(["甲乙丙丁", "戊己庚辛"]))
            else:
                results.append(
                    LineBreakResult(parts=[], outcome=OUTCOME_REQUEST_ERROR)
                )
        return results


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
    assert client.hint_calls[1] is not None
    assert client.hint_calls[1][0] is not None
    assert "改字" in (client.hint_calls[1][0] or "")


def test_llm_break_empty_outcome_gets_hint_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    text = "一二三四五六七八九十十一"
    client = _EmptyThenOkClient()

    result = llm_break_lines(
        text,
        max_chars=5,
        settings=settings,
        llm_client=client,
    )

    assert result.split("\n") == ["一二三四", "五六七八", "九十十一"]
    assert client.calls == 2
    assert client.hints[1] is not None
    assert client.hints[1][0] is not None
    assert "完整切分" in (client.hints[1][0] or "")


def test_llm_break_config_error_terminates_without_three_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    text = "一二三四五六七八九十十一"
    _ConfigErrorClient.calls = 0

    result = llm_break_lines(
        text,
        max_chars=5,
        settings=settings,
        llm_client=_ConfigErrorClient(),
    )

    assert result == text
    assert _ConfigErrorClient.calls == 1


def test_llm_break_keeps_successful_line_when_sibling_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    text = "甲乙丙丁戊己庚辛\n乙超长行一二三四五六"

    class _OncePartial(_PartialBatchClient):
        rounds = 0

        def break_lines(
            self,
            lines: list[str],
            max_chars: int,
            *,
            min_chars: int | None = None,
            retry_hints: Sequence[str | None] | None = None,
        ) -> list[LineBreakResult]:
            type(self).rounds += 1
            if type(self).rounds == 1:
                return super().break_lines(
                    lines, max_chars, min_chars=min_chars, retry_hints=retry_hints
                )
            # Subsequent retries only for the failed line
            return [
                parsed_line_break(["乙超长行一二", "三四五六"]) for _line in lines
            ]

    result = llm_break_lines(
        text,
        max_chars=5,
        settings=settings,
        llm_client=_OncePartial(),
    )

    lines = result.split("\n")
    assert lines[0:2] == ["甲乙丙丁", "戊己庚辛"]
    assert "乙超长行一二" in lines


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
            retry_hints: Sequence[str | None] | None = None,
        ) -> list[LineBreakResult]:
            return [
                parsed_line_break(
                    ["而如果", "加上往届未就业的"] if line == original else [line]
                )
                for line in lines
            ]

    result = llm_break_lines(
        text,
        max_chars=10,
        settings=settings,
        llm_client=_SemanticClient(),
    )

    assert result.split("\n") == ["短", "而如果", "加上往届未就业的"]


def test_llm_break_soft_retries_short_then_accepts_on_final(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Below min_chars is soft: retry with hint, accept on final attempt (not hard gate)."""
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    settings.min_chars = 4
    original = "发布满打满算才三周时间"

    class _ShortSegmentClient:
        calls = 0
        hints: list[str | None] = []

        def break_lines(
            self,
            lines: list[str],
            max_chars: int,
            *,
            min_chars: int | None = None,
            retry_hints: Sequence[str | None] | None = None,
        ) -> list[LineBreakResult]:
            type(self).calls += 1
            if retry_hints is not None:
                type(self).hints.extend(list(retry_hints))
            return [
                parsed_line_break(["发布满打", "满算才", "三周时间"])
                for _line in lines
            ]

    _ShortSegmentClient.calls = 0
    _ShortSegmentClient.hints = []
    result = llm_break_lines(
        original,
        max_chars=10,
        settings=settings,
        llm_client=_ShortSegmentClient(),
    )

    assert _ShortSegmentClient.calls == 3
    assert any(h and "过短" in h for h in _ShortSegmentClient.hints)
    # Final soft accept still runs short-line repair when neighbors fit.
    assert result.split("\n") == ["发布满打满算才", "三周时间"]


def test_llm_break_soft_retries_overlength_then_accepts_on_final(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    original = "一二三四五六七八九十十一"

    class _StillLongClient:
        calls = 0
        hints: list[str | None] = []

        def break_lines(
            self,
            lines: list[str],
            max_chars: int,
            *,
            min_chars: int | None = None,
            retry_hints: Sequence[str | None] | None = None,
        ) -> list[LineBreakResult]:
            type(self).calls += 1
            if retry_hints is not None:
                type(self).hints.extend(list(retry_hints))
            return [
                parsed_line_break(["一二三四五六", "七八九十十一"]) for _line in lines
            ]

    _StillLongClient.calls = 0
    _StillLongClient.hints = []
    result = llm_break_lines(
        original,
        max_chars=5,
        settings=settings,
        llm_client=_StillLongClient(),
    )

    assert _StillLongClient.calls == 5
    assert any(h and "超过" in h for h in _StillLongClient.hints)
    assert result.split("\n") == ["一二三四五六", "七八九十十一"]


def test_llm_break_repairs_single_char_parts_on_accept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Accepted LLM parts still get short-line repair when neighbors can merge."""
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    settings.min_chars = 2
    original = "边境是彻底疯狂了"

    class _SingleCharClient:
        def break_lines(
            self,
            lines: list[str],
            max_chars: int,
            *,
            min_chars: int | None = None,
            retry_hints: Sequence[str | None] | None = None,
        ) -> list[LineBreakResult]:
            return [
                parsed_line_break(["边境", "是", "彻底", "疯狂", "了"])
                for _line in lines
            ]

    result = llm_break_lines(
        original,
        max_chars=10,
        settings=settings,
        llm_client=_SingleCharClient(),
    )

    lines = result.split("\n")
    assert "是" not in lines
    assert "了" not in lines
    assert "".join(lines) == original


def test_llm_break_accepts_english_word_boundary_split(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Newline may replace a retained word-boundary space; write back both parts."""
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    original = "Hello world今天我们继续聊"

    class _BoundarySpaceClient:
        def break_lines(
            self,
            lines: list[str],
            max_chars: int,
            *,
            min_chars: int | None = None,
            retry_hints: Sequence[str | None] | None = None,
        ) -> list[LineBreakResult]:
            return [
                parsed_line_break(["Hello", "world今天我们继续聊"])
                for _line in lines
            ]

    result = llm_break_lines(
        original,
        max_chars=10,
        settings=settings,
        llm_client=_BoundarySpaceClient(),
    )

    assert result.split("\n") == ["Hello", "world今天我们继续聊"]
    assert result != original


def test_llm_break_not_split_hint_differs_from_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    original = "一二三四五六七八九十十一"

    class _ReturnOriginalClient:
        calls = 0
        hints: list[str | None] = []

        def break_lines(
            self,
            lines: list[str],
            max_chars: int,
            *,
            min_chars: int | None = None,
            retry_hints: Sequence[str | None] | None = None,
        ) -> list[LineBreakResult]:
            type(self).calls += 1
            if retry_hints is not None:
                type(self).hints.extend(list(retry_hints))
            if type(self).calls == 1:
                return [parsed_line_break([line]) for line in lines]
            return [
                parsed_line_break(["一二三四", "五六七八", "九十十一"])
                for _line in lines
            ]

    _ReturnOriginalClient.calls = 0
    _ReturnOriginalClient.hints = []
    result = llm_break_lines(
        original,
        max_chars=5,
        settings=settings,
        llm_client=_ReturnOriginalClient(),
    )
    assert result.split("\n") == ["一二三四", "五六七八", "九十十一"]
    non_null = [h for h in _ReturnOriginalClient.hints if h]
    assert non_null
    assert "多行" in non_null[0]
    assert "完整切分" not in non_null[0]


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


def test_llm_break_wave2_requeues_ancestor_after_short_split(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    settings.min_chars = 5
    ancestor = "可KK园区拆平不到半年"

    class _BadThenGoodClient:
        calls = 0
        seen_lines: list[list[str]] = []
        hints: list[str | None] = []

        def break_lines(
            self,
            lines: list[str],
            max_chars: int,
            *,
            min_chars: int | None = None,
            retry_hints: Sequence[str | None] | None = None,
            wave: int = 1,
        ) -> list[LineBreakResult]:
            type(self).calls += 1
            type(self).seen_lines.append(list(lines))
            if retry_hints is not None:
                type(self).hints.extend(list(retry_hints))
            if wave == 1:
                return [
                    parsed_line_break(["可KK", "园区拆平不到半年"]) for _line in lines
                ]
            return [
                parsed_line_break(["可KK园区拆平", "不到半年"]) for _line in lines
            ]

    _BadThenGoodClient.calls = 0
    _BadThenGoodClient.seen_lines = []
    _BadThenGoodClient.hints = []
    result = llm_break_lines(
        ancestor,
        max_chars=10,
        settings=settings,
        llm_client=_BadThenGoodClient(),
    )

    assert _BadThenGoodClient.calls >= 2
    assert _BadThenGoodClient.seen_lines[0] == [ancestor]
    assert any(batch == [ancestor] for batch in _BadThenGoodClient.seen_lines[1:])
    assert any(h and "长度返工" in h for h in _BadThenGoodClient.hints)
    assert result.split("\n") == ["可KK园区拆平", "不到半年"]


def test_llm_break_wave2_keeps_wave1_when_wave2_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    settings.min_chars = 5
    ancestor = "可KK园区拆平不到半年"

    class _BadThenEmptyClient:
        def break_lines(
            self,
            lines: list[str],
            max_chars: int,
            *,
            min_chars: int | None = None,
            retry_hints: Sequence[str | None] | None = None,
            wave: int = 1,
        ) -> list[LineBreakResult]:
            if wave == 1:
                return [
                    parsed_line_break(["可KK", "园区拆平不到半年"]) for _line in lines
                ]
            return [LineBreakResult(parts=[], outcome=OUTCOME_EMPTY) for _ in lines]

    result = llm_break_lines(
        ancestor,
        max_chars=10,
        settings=settings,
        llm_client=_BadThenEmptyClient(),
    )

    assert result.split("\n") == ["可KK", "园区拆平不到半年"]


def test_llm_break_wave2_skipped_when_wave1_compliant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    settings.min_chars = 2
    original = "一二三四五六七八九十十一"

    class _CountingMock(MockLlmClient):
        pass

    client = _CountingMock()
    result = llm_break_lines(
        original,
        max_chars=5,
        settings=settings,
        llm_client=client,
    )

    assert len(client.calls) == 1
    assert result.split("\n") == ["一二三四", "五六七八", "九十十一"]


def test_llm_break_wave2_progress_increases_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    settings.min_chars = 5
    ancestor = "可KK园区拆平不到半年"

    class _BadThenGoodClient:
        def break_lines(
            self,
            lines: list[str],
            max_chars: int,
            *,
            min_chars: int | None = None,
            retry_hints: Sequence[str | None] | None = None,
            wave: int = 1,
        ) -> list[LineBreakResult]:
            if wave == 1:
                return [
                    parsed_line_break(["可KK", "园区拆平不到半年"]) for _line in lines
                ]
            return [
                parsed_line_break(["可KK园区拆平", "不到半年"]) for _line in lines
            ]

    snapshots = list(
        iter_llm_break_lines(
            ancestor,
            max_chars=10,
            settings=settings,
            llm_client=_BadThenGoodClient(),
        )
    )
    assert snapshots
    _working, llm_current, llm_total = snapshots[-1]
    assert llm_total >= 2
    assert llm_current == llm_total


def test_llm_break_wave2_does_not_cross_slots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTREALM_LLM_API_KEY", "sk-test")
    settings = _configured_settings()
    settings.min_chars = 5
    line_a = "可KK园区拆平不到半年"
    line_b = "一二三四五六七八九十甲"

    class _PerLineClient:
        wave2_inputs: list[str] = []

        def break_lines(
            self,
            lines: list[str],
            max_chars: int,
            *,
            min_chars: int | None = None,
            retry_hints: Sequence[str | None] | None = None,
            wave: int = 1,
        ) -> list[LineBreakResult]:
            results: list[LineBreakResult] = []
            for line in lines:
                if wave == 2:
                    type(self).wave2_inputs.append(line)
                    if line == line_a:
                        results.append(
                            parsed_line_break(["可KK园区拆平", "不到半年"])
                        )
                    else:
                        results.append(
                            parsed_line_break(["一二三四五六", "七八九十甲"])
                        )
                    continue
                if line == line_a:
                    results.append(parsed_line_break(["可KK", "园区拆平不到半年"]))
                else:
                    results.append(
                        parsed_line_break(["一二三四五六", "七八九十甲"])
                    )
            return results

    _PerLineClient.wave2_inputs = []
    text = f"{line_a}\n{line_b}"
    result = llm_break_lines(
        text,
        max_chars=10,
        settings=settings,
        llm_client=_PerLineClient(),
    )

    assert line_a in _PerLineClient.wave2_inputs
    assert all(inp in (line_a, line_b) for inp in _PerLineClient.wave2_inputs)
    assert "可KK园区拆平" in result.split("\n")
    assert line_a[:2] + line_b not in "".join(result.split("\n"))
