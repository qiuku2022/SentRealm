"""Tests for pipeline step 1: punctuation removal."""

from __future__ import annotations

from sentrealm_core.models import DEFAULT_PUNCTUATION_KEEP, DEFAULT_PUNCTUATION_REMOVE
from sentrealm_core.pipeline.line_count import merge_empty_lines
from sentrealm_core.pipeline.punctuation import remove_punctuation_and_break_lines


def _lines(text: str) -> list[str]:
    return merge_empty_lines(text).split("\n")


def test_golden_sample_break_at_punctuation() -> None:
    text = "大家好，欢迎来到今天的节目。今天我们聊聊 AI 技术。"
    result = remove_punctuation_and_break_lines(
        text,
        punctuation_remove=DEFAULT_PUNCTUATION_REMOVE,
        punctuation_keep=DEFAULT_PUNCTUATION_KEEP,
    )
    assert _lines(result) == [
        "大家好",
        "欢迎来到今天的节目",
        "今天我们聊聊 AI 技术",
    ]


def test_keeps_default_percent_and_decimal_point() -> None:
    assert DEFAULT_PUNCTUATION_KEEP == ["%", "."]
    assert "％" in DEFAULT_PUNCTUATION_REMOVE
    text = "增长50%，版本1.2，下降20％。"
    result = remove_punctuation_and_break_lines(
        text,
        punctuation_remove=DEFAULT_PUNCTUATION_REMOVE,
        punctuation_keep=DEFAULT_PUNCTUATION_KEEP,
    )
    assert _lines(result) == ["增长50%", "版本1.2", "下降20"]


def test_keep_list_takes_precedence_over_remove_list() -> None:
    text = "第一句。第二句."
    result = remove_punctuation_and_break_lines(
        text,
        punctuation_remove=DEFAULT_PUNCTUATION_REMOVE,
        punctuation_keep=["。", "."],
    )
    assert result == text


def test_multi_char_keep_token_takes_precedence() -> None:
    text = "前半段——后半段。"
    result = remove_punctuation_and_break_lines(
        text,
        punctuation_remove=DEFAULT_PUNCTUATION_REMOVE,
        punctuation_keep=["——"],
    )
    assert _lines(result) == ["前半段——后半段"]


def test_multi_char_punctuation_em_dash() -> None:
    text = "先说重点——再展开。"
    result = remove_punctuation_and_break_lines(
        text,
        punctuation_remove=DEFAULT_PUNCTUATION_REMOVE,
        punctuation_keep=DEFAULT_PUNCTUATION_KEEP,
    )
    assert _lines(result) == ["先说重点", "再展开"]
