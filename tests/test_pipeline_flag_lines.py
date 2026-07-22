"""Tests for pipeline step 8: overlength line flagging."""

from __future__ import annotations

from sentrealm_core.pipeline.flag_lines import flag_overlength_lines


def test_flag_overlength_lines_zero_based() -> None:
    text = "短行\n这是一行明显超长的中文文本内容"
    assert flag_overlength_lines(text, max_chars=5) == [1]


def test_flag_returns_empty_when_all_lines_fit() -> None:
    text = "第一行\n第二行"
    assert flag_overlength_lines(text, max_chars=10) == []


def test_flag_marks_multiple_lines() -> None:
    text = "一二三四五六\n七八九十十一"
    assert flag_overlength_lines(text, max_chars=5) == [0, 1]
