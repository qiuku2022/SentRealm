"""Step 3/5/7: count characters per line and merge empty lines."""

from __future__ import annotations

import re

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_LETTER_RE = re.compile(r"[A-Za-z]")
_DIGIT_RE = re.compile(r"[0-9]")


def count_line_chars(line: str) -> int:
    """Count Chinese, English letters, and digits (spaces/punctuation excluded)."""
    count = 0
    for char in line:
        if _CJK_RE.match(char) or _LETTER_RE.match(char) or _DIGIT_RE.match(char):
            count += 1
    return count


def index_after_char_count(line: str, char_count: int) -> int:
    """Return split index after ``char_count`` countable characters from the start."""
    if char_count < 1:
        return 0
    seen = 0
    for index, char in enumerate(line):
        if _CJK_RE.match(char) or _LETTER_RE.match(char) or _DIGIT_RE.match(char):
            seen += 1
            if seen >= char_count:
                return index + 1
    return len(line)


def merge_empty_lines(text: str) -> str:
    """Drop blank lines; output must not contain empty rows between content."""
    lines = [line for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


def detect_and_merge_lines(text: str) -> str:
    """Merge empty lines after prior pipeline steps (step 3/5/7 helper)."""
    return merge_empty_lines(text)
