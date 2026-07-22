"""Preprocessing pipeline orchestration (Phase 1: full 8-step flow)."""

from __future__ import annotations

from collections.abc import Iterator

from sentrealm_core.llm import LlmClient, is_llm_configured
from sentrealm_core.models import PreprocessPhase, PreprocessProgress, PreprocessResult, Settings
from sentrealm_core.pipeline.break_lexicon import resolve_break_lexicon
from sentrealm_core.pipeline.flag_lines import flag_overlength_lines
from sentrealm_core.pipeline.line_count import detect_and_merge_lines
from sentrealm_core.pipeline.llm_break import iter_llm_break_lines, llm_break_lines
from sentrealm_core.pipeline.punctuation import remove_punctuation_and_break_lines
from sentrealm_core.pipeline.rule_break import rule_break_lines
from sentrealm_core.pipeline.whitespace import normalize_whitespace


class EmptyTextError(ValueError):
    """Raised when input text is empty or whitespace-only."""


def _progress_snapshot(
    *,
    original: str,
    working: str,
    max_chars: int,
    phase: PreprocessPhase,
    llm_current: int | None = None,
    llm_total: int | None = None,
) -> PreprocessProgress:
    lines = working.split("\n") if working else []
    return PreprocessProgress(
        original=original,
        processed=working,
        line_count=len(lines),
        flagged_lines=flag_overlength_lines(working, max_chars),
        phase=phase,
        llm_current=llm_current,
        llm_total=llm_total,
    )


def iter_preprocess(
    text: str,
    settings: Settings,
    llm_client: LlmClient | None = None,
) -> Iterator[PreprocessProgress | PreprocessResult]:
    """Run preprocessing, yielding incremental snapshots then the final result."""
    if not text.strip():
        raise EmptyTextError("text must not be empty or whitespace-only")

    max_chars = settings.max_chars
    working = remove_punctuation_and_break_lines(
        text,
        punctuation_remove=settings.punctuation_remove,
        punctuation_keep=settings.punctuation_keep,
    )
    working = normalize_whitespace(working)
    working = detect_and_merge_lines(working)
    lexicon = resolve_break_lexicon(settings)
    working = rule_break_lines(
        working,
        max_chars,
        lexicon=lexicon,
        min_chars=settings.min_chars,
    )
    working = detect_and_merge_lines(working)

    yield _progress_snapshot(
        original=text,
        working=working,
        max_chars=max_chars,
        phase="rules",
    )

    if is_llm_configured(settings):
        for working, llm_current, llm_total in iter_llm_break_lines(
            working,
            max_chars,
            settings,
            llm_client=llm_client,
        ):
            yield _progress_snapshot(
                original=text,
                working=working,
                max_chars=max_chars,
                phase="llm",
                llm_current=llm_current,
                llm_total=llm_total,
            )
    else:
        working = llm_break_lines(working, max_chars, settings, llm_client=llm_client)

    working = detect_and_merge_lines(working)
    flagged_lines = flag_overlength_lines(working, max_chars)
    lines = working.split("\n") if working else []
    yield PreprocessResult(
        original=text,
        processed=working,
        line_count=len(lines),
        flagged_lines=flagged_lines,
    )


def preprocess(
    text: str,
    settings: Settings,
    llm_client: LlmClient | None = None,
) -> PreprocessResult:
    """Run the full preprocessing pipeline and return a shared result shape."""
    result: PreprocessResult | None = None
    for item in iter_preprocess(text, settings, llm_client=llm_client):
        if isinstance(item, PreprocessResult):
            result = item
    assert result is not None
    return result
