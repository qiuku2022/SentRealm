"""Tests for local short-line repair inside one natural sentence."""

from sentrealm_core.pipeline.short_line_repair import repair_short_lines


def test_merges_short_part_when_combined_line_fits() -> None:
    assert repair_short_lines(
        ["一二三四", "五六七八九"],
        max_chars=10,
        min_chars=4,
    ) == ["一二三四五六七八九"]


def test_keeps_short_part_when_neither_merge_fits() -> None:
    assert repair_short_lines(
        ["一二三四五六七", "八九十甲", "乙丙丁戊己庚辛"],
        max_chars=10,
        min_chars=4,
    ) == ["一二三四五六七", "八九十甲", "乙丙丁戊己庚辛"]


def test_restores_required_space_when_merging_english_parts() -> None:
    assert repair_short_lines(
        ["Hello", "world"],
        max_chars=12,
        min_chars=4,
    ) == ["Hello world"]
