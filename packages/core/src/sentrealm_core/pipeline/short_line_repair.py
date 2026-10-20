"""Repair locally mergeable short segments without crossing natural sentences."""

from __future__ import annotations

import math

from typing import Iterable

from sentrealm_core.pipeline.line_count import count_line_chars
from sentrealm_core.pipeline.whitespace import normalize_whitespace_line


_DEFAULT_LEADING_PARTICLES = frozenset({"的", "地", "得", "了", "着", "过"})


def shift_leading_particles(
    lines: list[str],
    *,
    max_chars: int,
    particles: Iterable[str] | None = None,
) -> list[str]:
    """Shift line-initial structural/aspect particles to previous line if space permits."""
    repaired = [line.strip() for line in lines if line.strip()]
    if len(repaired) < 2:
        return repaired

    particle_set = (
        frozenset(p.strip() for p in particles if p.strip())
        if particles is not None
        else _DEFAULT_LEADING_PARTICLES
    )
    if not particle_set:
        return repaired

    sorted_particles = sorted(particle_set, key=len, reverse=True)

    changed = True
    while changed:
        changed = False
        index = 1
        while index < len(repaired):
            curr = repaired[index]
            matched = next((p for p in sorted_particles if curr.startswith(p)), None)
            if matched is not None:
                prev = repaired[index - 1]
                p_len = count_line_chars(matched)
                if count_line_chars(prev) + p_len <= max_chars:
                    repaired[index - 1] = prev + matched
                    remainder = curr[len(matched):].lstrip()
                    if remainder:
                        repaired[index] = remainder
                    else:
                        repaired.pop(index)
                    changed = True
                    break
            index += 1

    return repaired


def _merge_pair(left: str, right: str) -> str:
    return normalize_whitespace_line(f"{left} {right}")


def repair_short_lines(
    lines: list[str],
    *,
    max_chars: int,
    min_chars: int,
    particles: Iterable[str] | None = None,
) -> list[str]:
    """Merge adjacent short parts when their combined length still fits."""

    shifted = shift_leading_particles(
        lines, max_chars=max_chars, particles=particles
    )
    repaired = [line.strip() for line in shifted if line.strip()]
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
