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


def test_keeps_percent_sign() -> None:
    text = "增长50%，继续。"
    result = remove_punctuation_and_break_lines(
        text,
        punctuation_remove=DEFAULT_PUNCTUATION_REMOVE,
        punctuation_keep=DEFAULT_PUNCTUATION_KEEP,
    )
    assert _lines(result) == ["增长50%", "继续"]


def test_multi_char_punctuation_em_dash() -> None:
    text = "先说重点——再展开。"
    result = remove_punctuation_and_break_lines(
        text,
        punctuation_remove=DEFAULT_PUNCTUATION_REMOVE,
        punctuation_keep=DEFAULT_PUNCTUATION_KEEP,
    )
    assert _lines(result) == ["先说重点", "再展开"]
