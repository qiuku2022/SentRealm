"""Quality gate for LLM break results (product definition / ADR-005)."""

from __future__ import annotations

import math

from sentrealm_core.pipeline.line_count import count_line_chars


def min_chars_for(max_chars: int) -> int:
    """Suggested default when settings omit min_chars: max(2, ceil(max_chars / 3))."""
    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")
    return max(2, math.ceil(max_chars / 3))


def resolve_min_chars(max_chars: int, min_chars: int | None) -> int:
    """Use explicit min_chars when provided; otherwise derive from max_chars."""
    if min_chars is None:
        return min_chars_for(max_chars)
    if min_chars < 1:
        raise ValueError("min_chars must be >= 1")
    if min_chars > max_chars:
        raise ValueError("min_chars must be <= max_chars")
    return min_chars


def normalize_for_conservation(text: str) -> str:
    return text.strip()


def conservation_ok(original: str, parts: list[str]) -> bool:
    """True when joined trimmed parts equal trimmed original (no rewrite)."""
    joined = "".join(part.strip() for part in parts)
    return joined == normalize_for_conservation(original)


def length_ok(
    parts: list[str],
    max_chars: int,
    *,
    min_chars: int | None = None,
) -> bool:
    """Every non-empty part is within [min_chars, max_chars] countable chars."""
    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")
    floor = resolve_min_chars(max_chars, min_chars)
    for part in parts:
        line = part.strip()
        if not line:
            return False
        count = count_line_chars(line)
        if count < floor or count > max_chars:
            return False
    return True


def quality_ok(
    original: str,
    parts: list[str],
    max_chars: int,
    *,
    min_chars: int | None = None,
) -> bool:
    """Hard gate: non-empty parts, length bounds, and meaning conservation."""
    cleaned = [part.strip() for part in parts if part.strip()]
    if not cleaned:
        return False
    return length_ok(cleaned, max_chars, min_chars=min_chars) and conservation_ok(
        original, cleaned
    )


def llm_quality_ok(original: str, parts: list[str]) -> bool:
    """Semantic-first LLM gate: conservation, real split, shorter longest segment."""
    cleaned = [part.strip() for part in parts if part.strip()]
    if len(cleaned) < 2:
        return False
    if not conservation_ok(original, cleaned):
        return False
    original_count = count_line_chars(original)
    if original_count <= 0:
        return False
    longest = max(count_line_chars(part) for part in cleaned)
    return longest < original_count
