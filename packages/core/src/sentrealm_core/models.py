"""Domain models for SentRealm core."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Preset = Literal["landscape", "portrait", "custom"]
PreprocessPhase = Literal["rules", "llm"]

DEFAULT_PUNCTUATION_REMOVE: list[str] = [
    "，",
    "。",
    "！",
    "？",
    "：",
    "；",
    "——",
    "、",
    ",",
    ".",
    "!",
    "?",
    ";",
    ":",
    "“",
    "”",
    "‘",
    "’",
    '"',
    "'",
    "（",
    "）",
    "(",
    ")",
    "…",
]

DEFAULT_PUNCTUATION_KEEP: list[str] = ["%", "％"]

PRESET_MAX_CHARS: dict[Preset, int] = {
    "landscape": 15,
    "portrait": 10,
}

# Default min segment length (editable in settings; independent of preset).
DEFAULT_MIN_CHARS = 5


def _dedupe_strip_words(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in items:
        word = raw.strip()
        if not word or word in seen:
            continue
        seen.add(word)
        result.append(word)
    return result


def _default_break_lexicon_settings() -> BreakLexiconSettings:
    from sentrealm_core.pipeline.break_lexicon import bundled_break_lexicon_settings

    return bundled_break_lexicon_settings()


class BreakLexiconSettings(BaseModel):
    """User-editable break lexicon; maps to four bundled txt categories."""

    protected_words: list[str] = Field(default_factory=list)
    break_after_words: list[str] = Field(default_factory=list)
    break_after_chars: list[str] = Field(default_factory=list)
    break_before_words: list[str] = Field(default_factory=list)

    @field_validator(
        "protected_words",
        "break_after_words",
        "break_after_chars",
        "break_before_words",
        mode="before",
    )
    @classmethod
    def _coerce_lexicon_lists(cls, value: object) -> list[str]:
        if value is None:
            return []
        return list(value)  # type: ignore[arg-type]

    @model_validator(mode="after")
    def _normalize_and_validate(self) -> BreakLexiconSettings:
        self.protected_words = _dedupe_strip_words(self.protected_words)
        self.break_after_words = _dedupe_strip_words(self.break_after_words)
        self.break_before_words = _dedupe_strip_words(self.break_before_words)

        chars: list[str] = []
        seen_chars: set[str] = set()
        for raw in self.break_after_chars:
            char = raw.strip()
            if not char or char in seen_chars:
                continue
            if len(char) != 1:
                raise ValueError("each break_after_char must be exactly one character")
            seen_chars.add(char)
            chars.append(char)
        self.break_after_chars = chars

        for word in self.protected_words:
            if len(word) > 4:
                raise ValueError("protected_words entries must be at most 4 characters")

        for word in self.break_after_words:
            if not word:
                raise ValueError("break_after_words entries must not be empty")

        for word in self.break_before_words:
            if not word:
                raise ValueError("break_before_words entries must not be empty")

        return self


class Settings(BaseModel):
    """User configuration persisted in SQLite (ADR-004)."""

    preset: Preset = "landscape"
    max_chars: int = Field(default=15, ge=1)
    min_chars: int = Field(default=DEFAULT_MIN_CHARS, ge=1)
    punctuation_remove: list[str] = Field(default_factory=lambda: list(DEFAULT_PUNCTUATION_REMOVE))
    punctuation_keep: list[str] = Field(default_factory=lambda: list(DEFAULT_PUNCTUATION_KEEP))
    llm_enabled: bool = False
    llm_endpoint: str = ""
    llm_model: str = ""
    break_lexicon: BreakLexiconSettings = Field(default_factory=_default_break_lexicon_settings)

    @field_validator("punctuation_remove", "punctuation_keep", mode="before")
    @classmethod
    def _coerce_punctuation_lists(cls, value: object) -> list[str]:
        if value is None:
            return []
        return list(value)  # type: ignore[arg-type]

    @model_validator(mode="after")
    def _min_chars_not_above_max(self) -> Settings:
        if self.min_chars > self.max_chars:
            raise ValueError("min_chars must be <= max_chars")
        return self

    def apply_preset_linkage(self) -> Settings:
        """Align max_chars with preset (landscape→15, portrait→10)."""
        if self.preset in PRESET_MAX_CHARS:
            self.max_chars = PRESET_MAX_CHARS[self.preset]
        if self.min_chars > self.max_chars:
            self.min_chars = self.max_chars
        return self

    @classmethod
    def defaults(cls) -> Settings:
        return cls()


def apply_runtime_overrides(
    settings: Settings,
    *,
    preset: Preset | None = None,
    max_chars: int | None = None,
) -> Settings:
    """Apply CLI/MCP one-shot overrides without persisting (docs/cli-mcp.md)."""
    merged = settings.model_copy(deep=True)
    if preset is not None:
        merged.preset = preset
        merged.apply_preset_linkage()
    if max_chars is not None:
        merged.max_chars = max_chars
        merged.preset = "custom"
        if merged.min_chars > merged.max_chars:
            merged.min_chars = merged.max_chars
    return merged


class PreprocessResult(BaseModel):
    """Preprocessing output shared by HTTP / CLI / MCP."""

    original: str
    processed: str
    line_count: int = Field(ge=0)
    flagged_lines: list[int] = Field(default_factory=list)

    @field_validator("flagged_lines", mode="before")
    @classmethod
    def _coerce_flagged_lines(cls, value: object) -> list[int]:
        if value is None:
            return []
        return list(value)  # type: ignore[arg-type]


class PreprocessProgress(BaseModel):
    """Incremental preprocess snapshot for GUI streaming."""

    original: str
    processed: str
    line_count: int = Field(ge=0)
    flagged_lines: list[int] = Field(default_factory=list)
    phase: PreprocessPhase
    llm_current: int | None = None
    llm_total: int | None = None

    @field_validator("flagged_lines", mode="before")
    @classmethod
    def _coerce_flagged_lines(cls, value: object) -> list[int]:
        if value is None:
            return []
        return list(value)  # type: ignore[arg-type]
