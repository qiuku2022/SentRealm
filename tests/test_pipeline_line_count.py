"""Tests for pipeline step 3: line counting and empty-line merge."""

from __future__ import annotations

import pytest

from sentrealm_core.pipeline.line_count import (
    count_line_chars,
    detect_and_merge_lines,
    merge_empty_lines,
)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("大家好", 3),
        ("Hello world", 10),
        ("AI 技术", 4),
        ("增长50%", 4),
        ("   ", 0),
    ],
)
def test_count_line_chars(line: str, expected: int) -> None:
    assert count_line_chars(line) == expected


def test_merge_empty_lines() -> None:
    text = "第一行\n\n  \n第二行\n"
    assert merge_empty_lines(text) == "第一行\n第二行"


def test_detect_and_merge_lines_alias() -> None:
    text = "a\n\nb"
    assert detect_and_merge_lines(text) == merge_empty_lines(text)
