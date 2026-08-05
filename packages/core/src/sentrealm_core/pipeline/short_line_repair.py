"""Repair locally mergeable short segments without crossing natural sentences."""

from __future__ import annotations

import math

from sentrealm_core.pipeline.line_count import count_line_chars
from sentrealm_core.pipeline.whitespace import normalize_whitespace_line


def _merge_pair(left: str, right: str) -> str:
    return normalize_whitespace_line(f"{left} {right}")


def repair_short_lines(
    lines: list[str],
    *,
    max_chars: int,
    min_chars: int,
) -> list[str]:
    """Merge adjacent short parts when their combined length still fits."""

    repaired = [line.strip() for line in lines if line.strip()]
    preferred_min = max(min_chars, math.ceil(max_chars / 2))
    index = 0
    while index < len(repaired):
        if count_line_chars(repaired[index]) >= preferred_min:
            index += 1
            continue

        choices: list[tuple[int, int, str]] = []
        if index > 0:
            merged = _merge_pair(repaired[index - 1], repaired[index])
            count = count_line_chars(merged)
            if count <= max_chars:
                choices.append((abs(max_chars - count), index - 1, merged))
        if index + 1 < len(repaired):
            merged = _merge_pair(repaired[index], repaired[index + 1])
            count = count_line_chars(merged)
            if count <= max_chars:
                choices.append((abs(max_chars - count), index, merged))

        if not choices:
            index += 1
            continue

        _, merge_at, merged = min(choices)
        repaired[merge_at : merge_at + 2] = [merged]
        index = max(0, merge_at - 1)

    return repaired
