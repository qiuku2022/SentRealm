"""Step 1: remove punctuation and break lines at removal positions."""

from __future__ import annotations


def remove_punctuation_and_break_lines(
    text: str,
    *,
    punctuation_remove: list[str],
    punctuation_keep: list[str],
) -> str:
    """Remove configured punctuation; insert newline at each removed position."""
    remove_tokens = sorted(set(punctuation_remove), key=len, reverse=True)
    keep_set = set(punctuation_keep)
    parts: list[str] = []
    index = 0

    while index < len(text):
        matched = False
        for token in remove_tokens:
            if text.startswith(token, index):
                parts.append("\n")
                index += len(token)
                matched = True
                break
        if matched:
            continue

        char = text[index]
        if char in keep_set:
            parts.append(char)
        elif char in punctuation_remove:
            parts.append("\n")
        else:
            parts.append(char)
        index += 1

    return "".join(parts)
