"""Tests for local short-line repair inside one natural sentence."""

from sentrealm_core.pipeline.short_line_repair import repair_short_lines, shift_leading_particles


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


def test_shift_leading_particles_shifts_to_previous_line_when_space_fits() -> None:
    lines = ["而是学历供给端", "的大规模扩张"]
    assert shift_leading_particles(lines, max_chars=10) == [
        "而是学历供给端的",
        "大规模扩张",
    ]


def test_shift_leading_particles_does_not_shift_when_previous_line_is_full() -> None:
    lines = ["一二三四五六七八九十", "的大规模扩张"]
    assert shift_leading_particles(lines, max_chars=10) == [
        "一二三四五六七八九十",
        "的大规模扩张",
    ]


def test_shift_leading_particles_pops_empty_line_when_single_particle() -> None:
    lines = ["这也是一个重要", "的"]
    assert shift_leading_particles(lines, max_chars=10) == ["这也是一个重要的"]


def test_repair_short_lines_integrates_particle_shifting() -> None:
    lines = ["而是学历供给端", "的大规模扩张"]
    assert repair_short_lines(lines, max_chars=10, min_chars=5) == [
        "而是学历供给端的",
        "大规模扩张",
    ]


def test_shift_leading_particles_with_custom_particle_list() -> None:
    # When "在" is configured as a leading particle to shift
    lines = ["我们生活", "在这个伟大的时代"]
    assert shift_leading_particles(lines, max_chars=10, particles=["在"]) == [
        "我们生活在",
        "这个伟大的时代",
    ]
