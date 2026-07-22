"""Tests for pipeline step 2: whitespace normalization."""

from __future__ import annotations

import pytest

from sentrealm_core.pipeline.whitespace import normalize_whitespace_line


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Hello world", "Hello world"),
        ("使用 iPhone 拍摄", "使用 iPhone 拍摄"),
        ("AI 技术", "AI 技术"),
        ("iPhone 15", "iPhone 15"),
        ("2024 年", "2024年"),
        ("增长 50 %", "增长50%"),
    ],
    ids=[
        "english_word_space",
        "english_chinese_space",
        "ai_chinese_space",
        "english_digit_space",
        "digit_chinese_no_space",
        "digit_percent_no_space",
    ],
)
def test_golden_samples(raw: str, expected: str) -> None:
    assert normalize_whitespace_line(raw) == expected


def test_trims_leading_trailing_spaces() -> None:
    assert normalize_whitespace_line("  Hello world  ") == "Hello world"


def test_collapses_multiple_spaces() -> None:
    assert normalize_whitespace_line("Hello   world") == "Hello world"
