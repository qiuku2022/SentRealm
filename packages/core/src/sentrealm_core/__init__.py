"""SentRealm core — preprocessing pipeline, models, and settings store."""

from sentrealm_core.llm import (
    LlmClient,
    MockLlmClient,
    OpenAILlmClient,
    is_llm_configured,
    check_llm_connection,
)
from sentrealm_core.models import PreprocessResult, Preset, PreprocessProgress, PreprocessPhase, Settings, apply_runtime_overrides
from sentrealm_core.pipeline import EmptyTextError, iter_preprocess, preprocess
from sentrealm_core.store import SettingsStore, SqliteSettingsStore, default_config_path

__all__ = [
    "apply_runtime_overrides",
    "EmptyTextError",
    "iter_preprocess",
    "is_llm_configured",
    "LlmClient",
    "MockLlmClient",
    "OpenAILlmClient",
    "PreprocessPhase",
    "PreprocessProgress",
    "PreprocessResult",
    "Preset",
    "Settings",
    "SettingsStore",
    "SqliteSettingsStore",
    "default_config_path",
    "preprocess",
    "check_llm_connection",
]
