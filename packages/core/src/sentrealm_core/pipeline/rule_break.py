"""Step 4: globally choose natural break points for over-length lines."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from sentrealm_core.pipeline.break_lexicon import BreakLexicon, default_break_lexicon
from sentrealm_core.pipeline.line_count import count_line_chars, index_after_char_count
from sentrealm_core.pipeline.llm_quality import resolve_min_chars
from sentrealm_core.pipeline.punctuation import PunctuationBoundary
from sentrealm_core.pipeline.short_line_repair import repair_short_lines

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")

_ENGLISH_BOUNDARY_PENALTY = 5
_WORD_BOUNDARY_PENALTY = 7
_CHAR_BOUNDARY_PENALTY = 14
_DISCOURAGED_BOUNDARY_PENALTY = 24

# These positions often split a modifier from its head or an auxiliary from its
# predicate. Existing SQLite lexicons may still contain them, so the protection
# lives in the selector as well as in the new bundled defaults.
_DISCOURAGED_AFTER_CHARS = frozenset(
    {"的", "地", "得", "着", "就", "也", "还", "又", "到", "有"}
)
_DISCOURAGED_AFTER_WORDS = frozenset({"非常"})


@dataclass(frozen=True)
class _BreakCandidate:
    position: int
    penalty: int
    discouraged: bool = False


def rule_break_lines(
    text: str,
    max_chars: int,
    lexicon: BreakLexicon | None = None,
    *,
    min_chars: int | None = None,
    punctuation_boundaries: Sequence[Sequence[PunctuationBoundary]] | None = None,
) -> str:
    """Break only over-length lines using a globally optimal candidate path."""

    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")

    floor = resolve_min_chars(max_chars, min_chars)
    lex = lexicon or default_break_lexicon()
    lines = text.split("\n")
    if punctuation_boundaries is not None and len(punctuation_boundaries) != len(
        lines
    ):
        raise ValueError("punctuation_boundaries must align with text lines")

    output: list[str] = []
    for index, line in enumerate(lines):
        preferred = punctuation_boundaries[index] if punctuation_boundaries else ()
        parts = break_overlength_line(
            line,
            max_chars,
            floor,
            lex,
            punctuation_boundaries=preferred,
        )
        output.extend(repair_short_lines(parts, max_chars=max_chars, min_chars=floor))
    return "\n".join(output)


def break_overlength_line(
    line: str,
    max_chars: int,
    min_chars: int,
    lexicon: BreakLexicon,
    *,
    punctuation_boundaries: Iterable[PunctuationBoundary] = (),
) -> list[str]:
    """Return the best complete segmentation, containing local overflow if needed."""

    total = count_line_chars(line)
    if total <= max_chars:
        return [line]

    candidates = _find_break_candidates(line, lexicon, punctuation_boundaries)
    if not candidates:
        return [line]

    path = _best_complete_path(
        line,
        candidates,
        total=total,
        max_chars=max_chars,
        min_chars=min_chars,
    )
    if path is None:
        return [line]

    parts: list[str] = []
    start = 0
    for end in path:
        parts.append(line[start:end].strip())
        start = end
    return parts


def _best_complete_path(
    line: str,
    candidates: dict[int, _BreakCandidate],
    *,
    total: int,
    max_chars: int,
    min_chars: int,
) -> tuple[int, ...] | None:
    end_position = len(line)
    positions = [0, *sorted(candidates), end_position]
    segments_needed = max(1, math.ceil(total / max_chars))
    target = total / segments_needed
    preferred_min = max(min_chars, math.ceil(max_chars / 2))

    # position -> (score, path of segment end positions)
    best: dict[int, tuple[float, tuple[int, ...]]] = {0: (0.0, ())}
    for start_index, start in enumerate(positions[:-1]):
        state = best.get(start)
        if state is None:
            continue
        base_score, base_path = state
        start_candidate = candidates.get(start)

        for end in positions[start_index + 1 :]:
            segment = line[start:end].strip()
            count = count_line_chars(segment)
            if count < min_chars:
                continue

            end_candidate = candidates.get(end)
            if count < preferred_min and (
                (start_candidate is not None and start_candidate.discouraged)
                or (end_candidate is not None and end_candidate.discouraged)
            ):
                continue

            boundary_penalty = 0 if end == end_position else candidates[end].penalty
            short_penalty = max(0, preferred_min - count) * 5
            overflow = max(0, count - max_chars)
            overflow_penalty = (1000 + overflow**2 * 50) if overflow else 0
            length_penalty = (min(count, max_chars) - target) ** 2
            score = (
                base_score
                + boundary_penalty
                + short_penalty
                + overflow_penalty
                + length_penalty
            )
            path = (*base_path, end)
            previous = best.get(end)
            if previous is None or (score, len(path), path) < (
                previous[0],
                len(previous[1]),
                previous[1],
            ):
                best[end] = (score, path)

    final = best.get(end_position)
    return final[1] if final is not None else None


def _find_break_candidates(
    line: str,
    lexicon: BreakLexicon,
    punctuation_boundaries: Iterable[PunctuationBoundary],
) -> dict[int, _BreakCandidate]:
    candidates: dict[int, _BreakCandidate] = {}

    def add(position: int, penalty: int, *, discouraged: bool = False) -> None:
        if position <= 0 or position >= len(line):
            return
        previous = candidates.get(position)
        candidate = _BreakCandidate(position, penalty, discouraged)
        if previous is None or (penalty, discouraged) < (
            previous.penalty,
            previous.discouraged,
        ):
            candidates[position] = candidate

    for boundary in punctuation_boundaries:
        position = index_after_char_count(line, boundary.char_offset)
        while position < len(line) and count_line_chars(line[position]) == 0:
            position += 1
        add(position, boundary.penalty)

    _add_english_break_candidates(line, add)

    for word in lexicon.break_after_words:
        start = 0
        while start < len(line):
            index = line.find(word, start)
            if index == -1:
                break
            position = index + len(word)
            if not lexicon.splits_inside_protected(line, position):
                discouraged = word in _DISCOURAGED_AFTER_WORDS
                add(
                    position,
                    (
                        _DISCOURAGED_BOUNDARY_PENALTY
                        if discouraged
                        else _WORD_BOUNDARY_PENALTY
                    ),
                    discouraged=discouraged,
                )
            start = index + 1

    for char in lexicon.break_after_chars:
        start = 0
        while start < len(line):
            index = line.find(char, start)
            if index == -1:
                break
            position = index + 1
            if not lexicon.splits_inside_protected(line, position):
                discouraged = char in _DISCOURAGED_AFTER_CHARS
                add(
                    position,
                    _DISCOURAGED_BOUNDARY_PENALTY if discouraged else _CHAR_BOUNDARY_PENALTY,
                    discouraged=discouraged,
                )
            start = index + 1

    for word in lexicon.break_before_words:
        start = 0
        while start < len(line):
            index = line.find(word, start)
            if index == -1:
                break
            if not lexicon.splits_inside_protected(line, index):
                add(index, _WORD_BOUNDARY_PENALTY)
            start = index + 1

    return candidates


def _add_english_break_candidates(
    line: str,
    add: Callable[[int, int], None],
) -> None:
    for index in range(1, len(line)):
        if line[index] != " ":
            continue

        left = line[index - 1]
        right = line[index + 1] if index + 1 < len(line) else ""
        if left.isascii() and left.isalpha() and right.isascii() and right.isalpha():
            add(index + 1, _ENGLISH_BOUNDARY_PENALTY)
        elif left.isascii() and left.isalnum() and _CJK_RE.match(right):
            add(index + 1, _ENGLISH_BOUNDARY_PENALTY)
        elif _CJK_RE.match(left) and right.isascii() and right.isalpha():
            add(index + 1, _ENGLISH_BOUNDARY_PENALTY)
