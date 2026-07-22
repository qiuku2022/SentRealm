"""Load and query break-point lexicon data."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentrealm_core.models import BreakLexiconSettings, Settings

_LEXICON_DIR = Path(__file__).resolve().parent.parent / "data" / "break_lexicon"


def _read_word_list(path: Path) -> tuple[str, ...]:
    if not path.is_file():
        return ()
    words: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        words.append(line)
    return tuple(words)


@dataclass(frozen=True)
class BreakLexicon:
    """In-memory break-point lexicon."""

    protected_words: tuple[str, ...] = field(default_factory=tuple)
    break_after_words: tuple[str, ...] = field(default_factory=tuple)
    break_after_chars: frozenset[str] = field(default_factory=frozenset)
    break_before_words: tuple[str, ...] = field(default_factory=tuple)

    def protected_ranges(self, line: str) -> list[tuple[int, int]]:
        """Return inclusive (start, end) index ranges for protected words."""
        ranges: list[tuple[int, int]] = []
        for word in sorted(self.protected_words, key=len, reverse=True):
            start = 0
            while start < len(line):
                index = line.find(word, start)
                if index == -1:
                    break
                ranges.append((index, index + len(word) - 1))
                start = index + 1
        return _merge_ranges(ranges)

    def splits_inside_protected(self, line: str, position: int) -> bool:
        """True when split would cut inside a protected word."""
        for start, end in self.protected_ranges(line):
            if start < position <= end:
                return True
        return False


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not ranges:
        return []
    sorted_ranges = sorted(ranges)
    merged = [sorted_ranges[0]]
    for start, end in sorted_ranges[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + 1:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def load_break_lexicon(lexicon_dir: Path | None = None) -> BreakLexicon:
    """Load lexicon txt files from disk."""
    base = lexicon_dir or _LEXICON_DIR
    return BreakLexicon(
        protected_words=_read_word_list(base / "protected_words.txt"),
        break_after_words=_read_word_list(base / "break_after_words.txt"),
        break_after_chars=frozenset(_read_word_list(base / "break_after_chars.txt")),
        break_before_words=_read_word_list(base / "break_before_words.txt"),
    )


@lru_cache(maxsize=1)
def default_break_lexicon() -> BreakLexicon:
    return load_break_lexicon()


def bundled_break_lexicon_settings() -> BreakLexiconSettings:
    """Bundled txt defaults for migration, API, and restore-default."""
    from sentrealm_core.models import BreakLexiconSettings

    bundled = load_break_lexicon()
    return BreakLexiconSettings(
        protected_words=list(bundled.protected_words),
        break_after_words=list(bundled.break_after_words),
        break_after_chars=sorted(bundled.break_after_chars),
        break_before_words=list(bundled.break_before_words),
    )


def lexicon_from_settings(settings: BreakLexiconSettings) -> BreakLexicon:
    return BreakLexicon(
        protected_words=tuple(settings.protected_words),
        break_after_words=tuple(settings.break_after_words),
        break_after_chars=frozenset(settings.break_after_chars),
        break_before_words=tuple(settings.break_before_words),
    )


def resolve_break_lexicon(settings: Settings) -> BreakLexicon:
    """Resolve runtime lexicon from user Settings."""
    lexicon_settings = settings.break_lexicon
    if (
        not lexicon_settings.protected_words
        and not lexicon_settings.break_after_words
        and not lexicon_settings.break_after_chars
        and not lexicon_settings.break_before_words
    ):
        return load_break_lexicon()
    return lexicon_from_settings(lexicon_settings)
