"""Tests for pipeline step 1: punctuation removal."""

from __future__ import annotations

from sentrealm_core.models import DEFAULT_PUNCTUATION_KEEP, DEFAULT_PUNCTUATION_REMOVE
from sentrealm_core.pipeline.line_count import merge_empty_lines
from sentrealm_core.pipeline.punctuation import (
    NORMAL_BOUNDARY_PENALTY,
    STRONG_BOUNDARY_PENALTY,
    PunctuationBoundary,
    remove_punctuation_and_break_lines,
    strip_punctuation_with_boundaries,
)


def _lines(text: str) -> list[str]:
    return merge_empty_lines(text).split("\n")


def test_sentence_terminator_is_hard_and_comma_is_candidate() -> None:
    text = "大家好，欢迎来到今天的节目。今天我们聊聊 AI 技术。"
    sentences = strip_punctuation_with_boundaries(
        text,
        punctuation_remove=DEFAULT_PUNCTUATION_REMOVE,
        punctuation_keep=DEFAULT_PUNCTUATION_KEEP,
    )
    assert [sentence.text for sentence in sentences] == [
        "大家好欢迎来到今天的节目",
        "今天我们聊聊 AI 技术",
    ]
    assert sentences[0].boundaries == (
        PunctuationBoundary(char_offset=3, penalty=STRONG_BOUNDARY_PENALTY),
    )
    assert sentences[1].boundaries == ()


def test_keeps_percent_sign() -> None:
    text = "增长50%，继续。"
    result = remove_punctuation_and_break_lines(
        text,
        punctuation_remove=DEFAULT_PUNCTUATION_REMOVE,
        punctuation_keep=DEFAULT_PUNCTUATION_KEEP,
    )
    assert _lines(result) == ["增长50%继续"]


def test_multi_char_punctuation_em_dash_is_candidate() -> None:
    text = "先说重点——再展开。"
    sentences = strip_punctuation_with_boundaries(
        text,
        punctuation_remove=DEFAULT_PUNCTUATION_REMOVE,
        punctuation_keep=DEFAULT_PUNCTUATION_KEEP,
    )
    assert [sentence.text for sentence in sentences] == ["先说重点再展开"]
    assert sentences[0].boundaries == (
        PunctuationBoundary(char_offset=4, penalty=NORMAL_BOUNDARY_PENALTY),
    )


def test_quotes_and_brackets_are_strip_only() -> None:
    text = "每当“降息”两个字（再次）登上新闻。"
    sentences = strip_punctuation_with_boundaries(
        text,
        punctuation_remove=DEFAULT_PUNCTUATION_REMOVE,
        punctuation_keep=DEFAULT_PUNCTUATION_KEEP,
    )
    assert [sentence.text for sentence in sentences] == ["每当降息两个字再次登上新闻"]
    assert sentences[0].boundaries == ()


def test_unknown_custom_remove_token_is_strip_only_and_keep_wins() -> None:
    sentences = strip_punctuation_with_boundaries(
        "甲~乙+丙",
        punctuation_remove=["~", "+"],
        punctuation_keep=["+"],
    )
    assert [sentence.text for sentence in sentences] == ["甲乙+丙"]
    assert sentences[0].boundaries == ()
