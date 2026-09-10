"""Step 6: LLM send-pool line breaking with quality rework (ADR-005)."""

from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass

from sentrealm_core.llm import (
    OUTCOME_CONFIG_ERROR,
    OUTCOME_EMPTY,
    OUTCOME_PARSED,
    OUTCOME_REQUEST_ERROR,
    OUTCOME_TRUNCATED,
    LineBreakResult,
    LlmClient,
    OpenAILlmClient,
    is_llm_configured,
    llm_api_key,
)
from sentrealm_core.models import Settings
from sentrealm_core.pipeline.line_count import count_line_chars
from sentrealm_core.pipeline.llm_quality import (
    conservation_ok,
    is_soft_quality_code,
    llm_quality_diagnose,
    llm_quality_ok,
    resolve_min_chars,
)
from sentrealm_core.pipeline.short_line_repair import repair_short_lines

logger = logging.getLogger(__name__)

_BATCH_SIZE = 10
_MAX_ATTEMPTS = 3
_WAVE2_MAX_ATTEMPTS = 2

_WAVE2_HINT = (
    "长度返工：请重新切分整句。每行尽量落在最短行长与上限之间，各行长度接近；"
    "禁止单字行；不要拆开英文缩写与后接中文专名（如 KK园区）；"
    "只插入换行，不改字。"
)

_RETRY_HINTS: dict[str, str] = {
    OUTCOME_EMPTY: "上次没有输出完整切分，请只输出多行切分结果",
    OUTCOME_TRUNCATED: "上次没有输出完整切分，请只输出多行切分结果",
    OUTCOME_REQUEST_ERROR: "上次调用失败，请重新切分",
    "not_split": "上次未形成多行，请在语义边界插入换行",
    "conservation": "上次改变了原文，请只插入换行、不改字",
    "no_progress": "上次切分没有缩短最长行，请切开超长部分",
    "empty": "上次没有输出完整切分，请只输出多行切分结果",
    "still_overlength": "上次仍有行超过字数上限，请在语义边界继续切开，使每行不超过上限",
    "too_short": "上次出现过短行（含单字行），请把过短片段并入相邻意群，避免单字成行",
}


@dataclass
class _PoolItem:
    text: str
    ancestor_text: str
    slot_id: int
    attempts: int = 0
    wave: int = 1
    retry_hint: str | None = None


def llm_break_lines(
    text: str,
    max_chars: int,
    settings: Settings,
    llm_client: LlmClient | None = None,
) -> str:
    """Break over-length lines via LLM send pool when configured; else unchanged."""
    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")
    if not is_llm_configured(settings):
        return text

    working = text
    for working, _, _ in iter_llm_break_lines(
        text,
        max_chars,
        settings,
        llm_client=llm_client,
    ):
        pass
    return working


def iter_llm_break_lines(
    text: str,
    max_chars: int,
    settings: Settings,
    llm_client: LlmClient | None = None,
) -> Iterator[tuple[str, int, int]]:
    """Yield (processed_so_far, llm_current, llm_total) as pool items reach terminal state."""
    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")
    if not is_llm_configured(settings):
        return

    client = llm_client or _build_default_client(settings)
    lines = text.split("\n")
    slots: OrderedDict[int, list[str]] = OrderedDict(
        (index, [line]) for index, line in enumerate(lines)
    )

    pool: list[_PoolItem] = [
        _PoolItem(text=line, ancestor_text=line, slot_id=slot_id, attempts=0, wave=1)
        for slot_id, line in enumerate(lines)
        if count_line_chars(line) > max_chars
    ]
    llm_total = len(pool)
    if llm_total == 0:
        return

    llm_current = 0
    slot_accepted_split: set[int] = set()
    ancestors: dict[int, str] = {item.slot_id: item.ancestor_text for item in pool}

    for working, llm_current, llm_total in _drain_pool(
        pool,
        slots=slots,
        client=client,
        max_chars=max_chars,
        settings=settings,
        llm_current=llm_current,
        llm_total=llm_total,
        slot_accepted_split=slot_accepted_split,
        keep_wave1_on_abandon=False,
    ):
        yield working, llm_current, llm_total

    wave2 = _enqueue_wave2(
        slots,
        slot_accepted_split=slot_accepted_split,
        ancestors=ancestors,
        max_chars=max_chars,
        min_chars=settings.min_chars,
    )
    if not wave2:
        return

    llm_total += len(wave2)
    logger.info("LLM wave2 enqueue count=%s total=%s", len(wave2), llm_total)
    yield _flatten_slots(slots), llm_current, llm_total

    for working, llm_current, llm_total in _drain_pool(
        wave2,
        slots=slots,
        client=client,
        max_chars=max_chars,
        settings=settings,
        llm_current=llm_current,
        llm_total=llm_total,
        slot_accepted_split=slot_accepted_split,
        keep_wave1_on_abandon=True,
    ):
        yield working, llm_current, llm_total


def _enqueue_wave2(
    slots: OrderedDict[int, list[str]],
    *,
    slot_accepted_split: set[int],
    ancestors: dict[int, str],
    max_chars: int,
    min_chars: int,
) -> list[_PoolItem]:
    """Queue ancestor re-breaks for accepted splits that still violate length bounds."""
    wave2: list[_PoolItem] = []
    for slot_id in slot_accepted_split:
        parts = slots.get(slot_id, [])
        if not _slot_length_noncompliant(parts, max_chars, min_chars):
            continue
        ancestor = ancestors[slot_id]
        logger.info("LLM wave2 slot=%s length noncompliant; requeue ancestor", slot_id)
        wave2.append(
            _PoolItem(
                text=ancestor,
                ancestor_text=ancestor,
                slot_id=slot_id,
                attempts=0,
                wave=2,
                retry_hint=_WAVE2_HINT,
            )
        )
    return wave2


def _drain_pool(
    pool: list[_PoolItem],
    *,
    slots: OrderedDict[int, list[str]],
    client: LlmClient,
    max_chars: int,
    settings: Settings,
    llm_current: int,
    llm_total: int,
    slot_accepted_split: set[int],
    keep_wave1_on_abandon: bool,
) -> Iterator[tuple[str, int, int]]:
    in_pool: set[int] = {item.slot_id for item in pool}

    while pool:
        batch = pool[:_BATCH_SIZE]
        pool = pool[_BATCH_SIZE:]
        for item in batch:
            in_pool.discard(item.slot_id)

        results = _invoke_batch(client, batch, max_chars, settings)

        for item, result in zip(batch, results, strict=True):
            item.attempts += 1
            max_attempts = (
                _WAVE2_MAX_ATTEMPTS if item.wave == 2 else _MAX_ATTEMPTS
            )
            failure_code = _classify_attempt(
                item.ancestor_text,
                result,
                max_chars=max_chars,
                min_chars=settings.min_chars,
                attempts=item.attempts,
                max_attempts=max_attempts,
            )
            logger.info(
                "LLM pool slot=%s wave=%s attempt=%s outcome=%s fail=%s "
                "finish_reason=%s http_status=%s",
                item.slot_id,
                item.wave,
                item.attempts,
                result.outcome,
                failure_code,
                result.finish_reason,
                result.http_status,
            )

            if failure_code is None:
                slots[item.slot_id] = _finalize_accepted_parts(
                    item.ancestor_text,
                    result.parts,
                    max_chars=max_chars,
                    min_chars=settings.min_chars,
                )
                slot_accepted_split.add(item.slot_id)
                llm_current += 1
                continue

            if result.outcome == OUTCOME_CONFIG_ERROR:
                if not keep_wave1_on_abandon:
                    slots[item.slot_id] = [item.ancestor_text]
                    slot_accepted_split.discard(item.slot_id)
                else:
                    logger.info(
                        "LLM wave2 slot=%s config error; keep wave1 result",
                        item.slot_id,
                    )
                llm_current += 1
                continue

            if item.wave == 2:
                item.retry_hint = _RETRY_HINTS.get(failure_code, _WAVE2_HINT)
            else:
                item.retry_hint = _RETRY_HINTS.get(failure_code)

            if item.attempts < max_attempts:
                if item.slot_id not in in_pool:
                    pool.append(item)
                    in_pool.add(item.slot_id)
            else:
                if keep_wave1_on_abandon:
                    logger.info(
                        "LLM wave2 slot=%s exhausted; keep wave1 result",
                        item.slot_id,
                    )
                else:
                    slots[item.slot_id] = [item.ancestor_text]
                    slot_accepted_split.discard(item.slot_id)
                llm_current += 1

        yield _flatten_slots(slots), llm_current, llm_total


def _invoke_batch(
    client: LlmClient,
    batch: list[_PoolItem],
    max_chars: int,
    settings: Settings,
) -> list[LineBreakResult]:
    wave = batch[0].wave if batch else 1
    try:
        raw = client.break_lines(
            [item.text for item in batch],
            max_chars,
            min_chars=settings.min_chars,
            retry_hints=[item.retry_hint for item in batch],
            wave=wave,
        )
        if len(raw) != len(batch):
            logger.warning(
                "LLM batch size mismatch: got %s for %s items",
                len(raw),
                len(batch),
            )
            return [
                LineBreakResult(parts=[], outcome=OUTCOME_REQUEST_ERROR)
                for _ in batch
            ]
        return list(raw)
    except TypeError:
        # Test doubles / older clients without wave= support.
        try:
            raw = client.break_lines(
                [item.text for item in batch],
                max_chars,
                min_chars=settings.min_chars,
                retry_hints=[item.retry_hint for item in batch],
            )
            if len(raw) != len(batch):
                return [
                    LineBreakResult(parts=[], outcome=OUTCOME_REQUEST_ERROR)
                    for _ in batch
                ]
            return list(raw)
        except Exception:
            logger.exception("LLM batch failed; counting as quality attempt for batch")
            return [
                LineBreakResult(parts=[], outcome=OUTCOME_REQUEST_ERROR)
                for _ in batch
            ]
    except Exception:
        logger.exception("LLM batch failed; counting as quality attempt for batch")
        return [
            LineBreakResult(parts=[], outcome=OUTCOME_REQUEST_ERROR)
            for _ in batch
        ]


def _slot_length_noncompliant(
    parts: list[str],
    max_chars: int,
    min_chars: int,
) -> bool:
    floor = resolve_min_chars(max_chars, min_chars)
    cleaned = [part.strip() for part in parts if part.strip()]
    if not cleaned:
        return True
    for part in cleaned:
        count = count_line_chars(part)
        if count < floor or count > max_chars:
            return True
    return False


def _finalize_accepted_parts(
    original: str,
    parts: list[str],
    *,
    max_chars: int,
    min_chars: int,
) -> list[str]:
    """Strip empties, then merge locally short neighbors when conservation holds."""
    cleaned = [part.strip() for part in parts if part.strip()]
    floor = resolve_min_chars(max_chars, min_chars)
    repaired = repair_short_lines(cleaned, max_chars=max_chars, min_chars=floor)
    if conservation_ok(original, repaired) and llm_quality_ok(original, repaired):
        return repaired
    return cleaned


def _classify_attempt(
    original: str,
    result: LineBreakResult,
    *,
    max_chars: int,
    min_chars: int,
    attempts: int,
    max_attempts: int,
) -> str | None:
    """Return failure code, or None when the attempt should be written back."""
    if result.outcome == OUTCOME_CONFIG_ERROR:
        return OUTCOME_CONFIG_ERROR
    if result.outcome == OUTCOME_REQUEST_ERROR:
        return OUTCOME_REQUEST_ERROR
    if result.outcome == OUTCOME_EMPTY:
        return OUTCOME_EMPTY
    if result.outcome == OUTCOME_TRUNCATED:
        quality_fail = llm_quality_diagnose(
            original,
            result.parts,
            max_chars=max_chars,
            min_chars=min_chars,
        )
        if quality_fail is None:
            return None
        if is_soft_quality_code(quality_fail) and attempts >= max_attempts:
            if llm_quality_ok(original, result.parts):
                return None
        return (
            OUTCOME_TRUNCATED
            if not is_soft_quality_code(quality_fail)
            else quality_fail
        )
    if result.outcome != OUTCOME_PARSED:
        return OUTCOME_REQUEST_ERROR

    quality_fail = llm_quality_diagnose(
        original,
        result.parts,
        max_chars=max_chars,
        min_chars=min_chars,
    )
    if quality_fail is None:
        return None
    if is_soft_quality_code(quality_fail) and attempts >= max_attempts:
        if llm_quality_ok(original, result.parts):
            return None
    return quality_fail


def _flatten_slots(slots: OrderedDict[int, list[str]]) -> str:
    lines: list[str] = []
    for parts in slots.values():
        lines.extend(parts)
    return "\n".join(lines)


def _build_default_client(settings: Settings) -> LlmClient:
    api_key = llm_api_key()
    if api_key is None:
        raise RuntimeError("LLM API key is required when LLM is enabled")
    return OpenAILlmClient(
        endpoint=settings.llm_endpoint,
        model=settings.llm_model,
        api_key=api_key,
    )
