"""Quality gate for LLM break results (product definition / ADR-005)."""

from __future__ import annotations

from collections.abc import Sequence
import math
import re

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
    """True when trimmed parts align in order to the trimmed original.

    Between consecutive parts, ordinary ASCII spaces in the original may be
    consumed (newline substitutes a retained word-boundary space). In-part
    spaces and all other characters must match exactly; no rewrite, reorder,
    or leftover text.
    """
    text = normalize_for_conservation(original)
    cleaned = [part.strip() for part in parts if part.strip()]
    if not cleaned:
        return not text

    pos = 0
    for index, part in enumerate(cleaned):
        if index > 0:
            while pos < len(text) and text[pos] == " ":
                pos += 1
        if not text.startswith(part, pos):
            return False
        pos += len(part)
    return pos == len(text)


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


_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_FORBIDDEN_LINE_START_CHARS = frozenset({"的", "地", "得", "了", "着", "过"})
_DISCOURAGED_NEGATION_ENDINGS = (
    "不能", "不可", "不要", "决不", "绝不", "从不", "严禁", "拒绝",
    "不得不", "并不会", "并不", "毫无", "绝非", "无法",
)


def has_bad_semantic_split(
    parts: Sequence[str],
    *,
    particles: Sequence[str] | None = None,
) -> bool:
    """True when split breaks tightly bound negative predicates or hangs particles."""
    forbidden = (
        frozenset(particles) if particles is not None else _FORBIDDEN_LINE_START_CHARS
    )
    cleaned = [part.strip() for part in parts if part.strip()]
    if len(cleaned) < 2:
        return False
    for i in range(1, len(cleaned)):
        prev = cleaned[i - 1]
        curr = cleaned[i]
        if not curr or not prev:
            continue
        # 1. Non-first line starts with forbidden structural particle
        if any(curr.startswith(p) for p in forbidden):
            return True
        # 2. Previous line ends with multi-character negation phrase
        if any(prev.endswith(neg) for neg in _DISCOURAGED_NEGATION_ENDINGS):
            return True
        # 3. Single-character negation at line end before a Chinese character
        if prev[-1] in {"不", "没", "非", "未"} and _CJK_RE.match(curr[:1]):
            return True
    return False


_SOFT_CODES = frozenset({"still_overlength", "too_short", "bad_semantic_split"})


def llm_quality_diagnose(
    original: str,
    parts: list[str],
    *,
    max_chars: int | None = None,
    min_chars: int | None = None,
    particles: Sequence[str] | None = None,
) -> str | None:
    """Return None when LLM quality passes; else a fixed failure code.

    Hard codes: empty | not_split | conservation | no_progress
    Soft codes (only when max_chars / min_chars provided): still_overlength | too_short
    Soft codes are for retry hints; they are not hard write-back gates.
    """
    cleaned = [part.strip() for part in parts if part.strip()]
    if not cleaned:
        return "empty"
    if len(cleaned) < 2:
        return "not_split"
    if not conservation_ok(original, cleaned):
        return "conservation"
    original_count = count_line_chars(original)
    if original_count <= 0:
        return "no_progress"
    longest = max(count_line_chars(part) for part in cleaned)
    if longest >= original_count:
        return "no_progress"

    if max_chars is not None:
        if max_chars < 1:
            raise ValueError("max_chars must be >= 1")
        for part in cleaned:
            if count_line_chars(part) > max_chars:
                return "still_overlength"

    if min_chars is not None:
        floor = resolve_min_chars(max_chars if max_chars is not None else min_chars, min_chars)
        for part in cleaned:
            if count_line_chars(part) < floor:
                return "too_short"

    if max_chars is not None or min_chars is not None:
        if has_bad_semantic_split(cleaned, particles=particles):
            return "bad_semantic_split"

    return None


def llm_quality_ok(
    original: str,
    parts: list[str],
    *,
    max_chars: int | None = None,
    min_chars: int | None = None,
    particles: Sequence[str] | None = None,
) -> bool:
    """LLM gate: conservation, real split (>=2 parts), and progress.

    Does not hard-reject on min_chars / max_chars. When those are passed,
    soft length codes still fail this helper — callers that need the hard-only
    gate should omit them (or use diagnose and ignore soft codes).
    """
    return (
        llm_quality_diagnose(
            original,
            parts,
            max_chars=max_chars,
            min_chars=min_chars,
            particles=particles,
        )
        is None
    )


def is_soft_quality_code(code: str | None) -> bool:
    return code in _SOFT_CODES
