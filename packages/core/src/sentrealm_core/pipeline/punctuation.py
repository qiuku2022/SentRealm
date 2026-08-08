"""Step 1: remove punctuation and break lines at removal positions."""

from __future__ import annotations


def remove_punctuation_and_break_lines(
    text: str,
    *,
    punctuation_remove: list[str],
    punctuation_keep: list[str],
) -> str:
    """Remove configured punctuation; insert newline at each removed position."""
    keep_tokens = sorted(
        {token for token in punctuation_keep if token}, key=len, reverse=True
    )
    remove_tokens = sorted(
        {token for token in punctuation_remove if token}, key=len, reverse=True
    )
    parts: list[str] = []
    index = 0

    while index < len(text):
        kept = False
        for token in keep_tokens:
            if text.startswith(token, index):
                parts.append(token)
                index += len(token)
                kept = True
                break
        if kept:
            continue

        matched = False
        for token in remove_tokens:
            if text.startswith(token, index):
                parts.append("\n")
                index += len(token)
                matched = True
                break
        if matched:
            continue

        parts.append(text[index])
        index += 1

    return "".join(parts)
