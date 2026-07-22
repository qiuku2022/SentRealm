"""Step 4: rule-based line breaking using break lexicon."""

from __future__ import annotations

import math
import re

from sentrealm_core.pipeline.break_lexicon import BreakLexicon, default_break_lexicon
from sentrealm_core.pipeline.line_count import count_line_chars
from sentrealm_core.pipeline.llm_quality import resolve_min_chars

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def rule_break_lines(
    text: str,
    max_chars: int,
    lexicon: BreakLexicon | None = None,
    *,
    min_chars: int | None = None,
) -> str:
    """Break only lines exceeding max_chars at whitelisted break points."""
    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")

    floor = resolve_min_chars(max_chars, min_chars)
    lex = lexicon or default_break_lexicon()
    output: list[str] = []
    for line in text.split("\n"):
        output.extend(_break_long_line(line, max_chars, floor, lex))
    return "\n".join(output)


def _ideal_first_segment_chars(total: int, max_chars: int) -> float:
    """Target length for the first segment when packing into ceil(total/max) rows."""
    segments_needed = max(1, math.ceil(total / max_chars))
    return total / segments_needed


def _break_long_line(
    line: str,
    max_chars: int,
    min_chars: int,
    lexicon: BreakLexicon,
) -> list[str]:
    segments: list[str] = []
    current = line

    while count_line_chars(current) > max_chars:
        candidates = _valid_break_positions(current, max_chars, min_chars, lexicon)
        if not candidates:
            segments.append(current)
            return segments

        total = count_line_chars(current)
        ideal = _ideal_first_segment_chars(total, max_chars)
        best = min(
            candidates,
            key=lambda pos: (
                abs(count_line_chars(current[:pos].rstrip()) - ideal),
                -count_line_chars(current[:pos].rstrip()),
            ),
        )
        left = current[:best].rstrip()
        current = current[best:].lstrip()
        segments.append(left)

    segments.append(current)
    return segments


def _valid_break_positions(
    line: str,
    max_chars: int,
    min_chars: int,
    lexicon: BreakLexicon,
) -> list[int]:
    positions = _find_break_positions(line, lexicon)
    valid: list[int] = []
    for pos in positions:
        if lexicon.splits_inside_protected(line, pos):
            continue
        if _is_valid_split(line, pos, max_chars, min_chars):
            valid.append(pos)
    return valid


def _find_break_positions(line: str, lexicon: BreakLexicon) -> set[int]:
    positions: set[int] = set()
    _add_english_break_positions(line, positions)

    for word in lexicon.break_after_words:
        start = 0
        while start < len(line):
            index = line.find(word, start)
            if index == -1:
                break
            positions.add(index + len(word))
            start = index + 1

    for char in lexicon.break_after_chars:
        start = 0
        protected_ends = {end for start, end in lexicon.protected_ranges(line)}
        while start < len(line):
            index = line.find(char, start)
            if index == -1:
                break
            if char == "的" and index > 0 and (index - 1) in protected_ends:
                start = index + 1
                continue
            positions.add(index + 1)
            start = index + 1

    for word in lexicon.break_before_words:
        start = 0
        while start < len(line):
            index = line.find(word, start)
            if index == -1:
                break
            positions.add(index)
            start = index + 1

    return positions


def _add_english_break_positions(line: str, positions: set[int]) -> None:
    for index in range(1, len(line)):
        if line[index] != " ":
            continue

        left = line[index - 1]
        right = line[index + 1] if index + 1 < len(line) else ""

        if left.isascii() and left.isalpha() and right.isascii() and right.isalpha():
            positions.add(index + 1)
        elif left.isascii() and left.isalnum() and _CJK_RE.match(right):
            positions.add(index + 1)
        elif _CJK_RE.match(left) and right.isascii() and right.isalpha():
            positions.add(index + 1)


def _is_valid_split(line: str, position: int, max_chars: int, min_chars: int) -> bool:
    left = line[:position].rstrip()
    right = line[position:].lstrip()
    left_count = count_line_chars(left)
    right_count = count_line_chars(right)

    if left_count == 0 or right_count == 0:
        return False
    if left_count < min_chars or right_count < min_chars:
        return False
    return left_count <= max_chars
