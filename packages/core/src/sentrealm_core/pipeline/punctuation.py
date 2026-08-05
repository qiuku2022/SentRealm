"""Step 1: remove punctuation while preserving useful break boundaries."""

from __future__ import annotations

from dataclasses import dataclass

from sentrealm_core.pipeline.line_count import count_line_chars

# Source newlines and sentence terminators form natural-sentence boundaries.
_HARD_BREAK_TOKENS = frozenset({"。", "！", "？", ".", "!", "?"})
# Clause punctuation is preferred when an over-length sentence needs splitting.
_STRONG_CANDIDATE_TOKENS = frozenset({"，", ",", "；", ";", "：", ":"})
# Enumeration / pause punctuation is useful, but weaker than clause punctuation.
_NORMAL_CANDIDATE_TOKENS = frozenset({"、", "——", "…"})

STRONG_BOUNDARY_PENALTY = 0
NORMAL_BOUNDARY_PENALTY = 4


@dataclass(frozen=True)
class PunctuationBoundary:
    """A removable punctuation position measured in countable characters."""

    char_offset: int
    penalty: int


@dataclass(frozen=True)
class NaturalSentence:
    """Cleaned natural sentence plus optional internal punctuation boundaries."""

    text: str
    boundaries: tuple[PunctuationBoundary, ...] = ()


def strip_punctuation_with_boundaries(
    text: str,
    *,
    punctuation_remove: list[str],
    punctuation_keep: list[str],
) -> list[NaturalSentence]:
    """Remove configured punctuation and retain ranked break candidates.

    Removed sentence terminators and source newlines end a natural sentence.
    Clause / enumeration punctuation is removed but only recorded as a candidate;
    quotes, brackets, and unknown custom tokens are removed without forcing a break.
    ``char_offset`` is stable across whitespace normalization because whitespace is
    not countable under the product character-counting rules.
    """

    remove_tokens = sorted(set(punctuation_remove), key=len, reverse=True)
    keep_tokens = sorted(set(punctuation_keep), key=len, reverse=True)
    sentences: list[NaturalSentence] = []
    parts: list[str] = []
    boundaries: dict[int, int] = {}
    countable_chars = 0

    def append_text(value: str) -> None:
        nonlocal countable_chars
        parts.append(value)
        countable_chars += count_line_chars(value)

    def add_boundary(penalty: int) -> None:
        if countable_chars <= 0:
            return
        previous = boundaries.get(countable_chars)
        boundaries[countable_chars] = (
            penalty if previous is None else min(previous, penalty)
        )

    def flush_sentence() -> None:
        nonlocal parts, boundaries, countable_chars
        value = "".join(parts)
        if value.strip():
            valid_boundaries = tuple(
                PunctuationBoundary(offset, penalty)
                for offset, penalty in sorted(boundaries.items())
                if 0 < offset < countable_chars
            )
            sentences.append(NaturalSentence(value, valid_boundaries))
        parts = []
        boundaries = {}
        countable_chars = 0

    index = 0
    while index < len(text):
        if text.startswith("\r\n", index):
            flush_sentence()
            index += 2
            continue
        if text[index] in {"\r", "\n"}:
            flush_sentence()
            index += 1
            continue

        kept = next(
            (token for token in keep_tokens if text.startswith(token, index)),
            None,
        )
        if kept is not None:
            append_text(kept)
            index += len(kept)
            continue

        removed = next(
            (token for token in remove_tokens if text.startswith(token, index)),
            None,
        )
        if removed is None:
            append_text(text[index])
            index += 1
            continue

        if removed in _HARD_BREAK_TOKENS:
            flush_sentence()
        elif removed in _STRONG_CANDIDATE_TOKENS:
            add_boundary(STRONG_BOUNDARY_PENALTY)
        elif removed in _NORMAL_CANDIDATE_TOKENS:
            add_boundary(NORMAL_BOUNDARY_PENALTY)
        # Quotes, brackets, and unknown custom tokens are strip-only.
        index += len(removed)

    flush_sentence()
    return sentences


def remove_punctuation_and_break_lines(
    text: str,
    *,
    punctuation_remove: list[str],
    punctuation_keep: list[str],
) -> str:
    """Compatibility helper returning cleaned natural sentences as text lines."""

    sentences = strip_punctuation_with_boundaries(
        text,
        punctuation_remove=punctuation_remove,
        punctuation_keep=punctuation_keep,
    )
    return "\n".join(sentence.text for sentence in sentences)
