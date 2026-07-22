"""HTTP request/response schemas aligned with docs/api/openapi.yaml."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from sentrealm_core.models import PreprocessResult, Settings


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class PreprocessRequest(BaseModel):
    text: str
    settings: Settings | None = None


class PreprocessResponse(PreprocessResult):
    """Alias of core PreprocessResult for OpenAPI clarity."""

    pass


SettingsResponse = Settings


class LlmTestResponse(BaseModel):
    ok: bool
    skipped: bool = False
    message: str | None = None
