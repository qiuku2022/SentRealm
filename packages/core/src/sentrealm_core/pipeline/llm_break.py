"""Step 6: LLM send-pool line breaking with quality rework (ADR-005)."""

from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass

from sentrealm_core.llm import LlmClient, OpenAILlmClient, is_llm_configured, llm_api_key
from sentrealm_core.models import Settings
from sentrealm_core.pipeline.line_count import count_line_chars
from sentrealm_core.pipeline.llm_quality import llm_quality_ok

logger = logging.getLogger(__name__)

_BATCH_SIZE = 10
_MAX_ATTEMPTS = 3


@dataclass
class _PoolItem:
    text: str
    slot_id: int
    attempts: int = 0


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
        _PoolItem(text=line, slot_id=slot_id, attempts=0)
        for slot_id, line in enumerate(lines)
        if count_line_chars(line) > max_chars
    ]
    llm_total = len(pool)
    if llm_total == 0:
        return

    llm_current = 0
    in_pool: set[int] = {item.slot_id for item in pool}

    while pool:
        batch = pool[:_BATCH_SIZE]
        pool = pool[_BATCH_SIZE:]
        for item in batch:
            in_pool.discard(item.slot_id)

        results: list[list[str] | None]
        try:
            raw = client.break_lines(
                [item.text for item in batch],
                max_chars,
                min_chars=settings.min_chars,
            )
            if len(raw) != len(batch):
                logger.warning(
                    "LLM batch size mismatch: got %s for %s items",
                    len(raw),
                    len(batch),
                )
                results = [None] * len(batch)
            else:
                results = list(raw)
        except Exception:
            logger.exception("LLM batch failed; counting as quality attempt for batch")
            results = [None] * len(batch)

        for item, parts in zip(batch, results, strict=True):
            item.attempts += 1
            if parts is not None and llm_quality_ok(
                item.text,
                parts,
                min_chars=settings.min_chars,
            ):
                slots[item.slot_id] = [part.strip() for part in parts if part.strip()]
                llm_current += 1
            elif item.attempts < _MAX_ATTEMPTS:
                if item.slot_id not in in_pool:
                    pool.append(item)
                    in_pool.add(item.slot_id)
            else:
                slots[item.slot_id] = [item.text]
                llm_current += 1

        yield _flatten_slots(slots), llm_current, llm_total


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
