"""Step 8: mark lines that still exceed max_chars after prior steps."""

from __future__ import annotations

from sentrealm_core.pipeline.line_count import count_line_chars


def flag_overlength_lines(text: str, max_chars: int) -> list[int]:
    """Return 0-based line indices still over the character limit."""
    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")
    return [
        index
        for index, line in enumerate(text.split("\n"))
        if count_line_chars(line) > max_chars
    ]
