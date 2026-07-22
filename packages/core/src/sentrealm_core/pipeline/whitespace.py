"""Step 2: normalize whitespace per product rules (single-line in/out)."""

from __future__ import annotations

import re

_CJK = r"[\u4e00-\u9fff\u3400-\u4dbf]"
_LETTER = r"[A-Za-z]"
_DIGIT = r"[0-9]"
_PCT = r"[%％]"

_RE_CJK_DIGIT = re.compile(rf"({_CJK})\s+({_DIGIT})")
_RE_DIGIT_CJK = re.compile(rf"({_DIGIT})\s+({_CJK})")
_RE_DIGIT_PCT = re.compile(rf"({_DIGIT})\s+({_PCT})")
_RE_CJK_CJK = re.compile(rf"({_CJK})\s+({_CJK})")
_RE_MULTI_SPACE = re.compile(r" {2,}")


def normalize_whitespace_line(line: str) -> str:
    """Normalize spaces on one line (after punctuation removal, before breaking)."""
    normalized = line.strip()
    if not normalized:
        return ""

    normalized = _RE_CJK_DIGIT.sub(r"\1\2", normalized)
    normalized = _RE_DIGIT_CJK.sub(r"\1\2", normalized)
    normalized = _RE_DIGIT_PCT.sub(r"\1\2", normalized)
    normalized = _RE_CJK_CJK.sub(r"\1\2", normalized)
    normalized = _RE_MULTI_SPACE.sub(" ", normalized)
    return normalized.strip()


def normalize_whitespace(text: str) -> str:
    """Apply whitespace normalization to each line."""
    lines = text.split("\n")
    return "\n".join(normalize_whitespace_line(line) for line in lines)
