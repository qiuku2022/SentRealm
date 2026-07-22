"""Phase 0 HTTP routes — delegate to sentrealm_core only."""

from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from sentrealm_core import check_llm_connection, iter_preprocess, preprocess
from sentrealm_core.llm import is_llm_configured
from sentrealm_core.models import BreakLexiconSettings, PreprocessProgress, PreprocessResult
from sentrealm_core.pipeline import EmptyTextError
from sentrealm_core.pipeline.break_lexicon import bundled_break_lexicon_settings

from apps.gui.api.dependencies import StoreDep
from apps.gui.api.schemas import (
    HealthResponse,
    LlmTestResponse,
    PreprocessRequest,
    PreprocessResponse,
    SettingsResponse,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse()


settings_router = APIRouter(prefix="/api/v1")


@settings_router.get("/settings", response_model=SettingsResponse)
def get_settings(store: StoreDep) -> SettingsResponse:
    return store.load()


@settings_router.put("/settings", response_model=SettingsResponse)
def put_settings(body: SettingsResponse, store: StoreDep) -> SettingsResponse:
    store.save(body)
    return store.load()


@settings_router.get("/break-lexicon/defaults", response_model=BreakLexiconSettings)
def get_break_lexicon_defaults() -> BreakLexiconSettings:
    return bundled_break_lexicon_settings()


@settings_router.get("/settings/llm-key-status")
def get_llm_key_status() -> dict[str, bool]:
    import os

    configured = bool(os.environ.get("SENTREALM_LLM_API_KEY", "").strip())
    return {"configured": configured}


@settings_router.post("/settings/llm-test", response_model=LlmTestResponse)
def post_llm_test(store: StoreDep) -> LlmTestResponse:
    settings = store.load()
    if not is_llm_configured(settings):
        return LlmTestResponse(ok=True, skipped=True)

    error = check_llm_connection(settings)
    if error:
        return LlmTestResponse(ok=False, message=error)
    return LlmTestResponse(ok=True)


@settings_router.post("/preprocess", response_model=PreprocessResponse)
def post_preprocess(body: PreprocessRequest, store: StoreDep) -> PreprocessResponse:
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="文稿不能为空")

    settings = body.settings if body.settings is not None else store.load()

    try:
        result = preprocess(body.text, settings)
    except EmptyTextError as exc:
        raise HTTPException(status_code=400, detail="文稿不能为空") from exc

    return PreprocessResponse.model_validate(result.model_dump())


def _sse_payload(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _iter_preprocess_events(
    text: str,
    settings,
) -> Iterator[str]:
    try:
        for item in iter_preprocess(text, settings):
            if isinstance(item, PreprocessProgress):
                payload = {"type": "progress", **item.model_dump(mode="json")}
                yield _sse_payload(payload)
            else:
                assert isinstance(item, PreprocessResult)
                payload = {"type": "done", **item.model_dump(mode="json")}
                yield _sse_payload(payload)
    except EmptyTextError:
        yield _sse_payload({"type": "error", "detail": "文稿不能为空"})


@settings_router.post("/preprocess/stream")
def post_preprocess_stream(body: PreprocessRequest, store: StoreDep) -> StreamingResponse:
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="文稿不能为空")

    settings = body.settings if body.settings is not None else store.load()
    return StreamingResponse(
        _iter_preprocess_events(body.text, settings),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
