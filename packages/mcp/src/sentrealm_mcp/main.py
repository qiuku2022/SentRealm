"""MCP server — direct core access, no HTTP (ADR-007)."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from sentrealm_core import (
    SqliteSettingsStore,
    apply_runtime_overrides,
    preprocess,
)
from sentrealm_core.pipeline import EmptyTextError
from sentrealm_core.store import SettingsStore

mcp = FastMCP("sentrealm")


def get_store() -> SettingsStore:
    return SqliteSettingsStore()


@mcp.tool(name="preprocess_text")
def preprocess_text(
    text: str,
    preset: Literal["landscape", "portrait"] | None = None,
    max_chars: int | None = None,
) -> dict[str, Any]:
    """Preprocess manuscript text; returns PreprocessResponse-shaped JSON."""
    if not text.strip():
        raise ValueError("text must not be empty or whitespace-only")

    settings = apply_runtime_overrides(
        get_store().load(),
        preset=preset,
        max_chars=max_chars,
    )

    try:
        result = preprocess(text, settings)
    except EmptyTextError as exc:
        raise ValueError("text must not be empty or whitespace-only") from exc

    return result.model_dump(mode="json")


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
