"""Tests for pipeline step 4: rule-based breaking."""

from __future__ import annotations

from sentrealm_core.pipeline.break_lexicon import BreakLexicon
from sentrealm_core.pipeline.line_count import count_line_chars
from sentrealm_core.pipeline.rule_break import rule_break_lines


def test_does_not_use_risky_particle_cut_to_force_complete_segmentation() -> None:
    line = "使用 iPhone 15 拍摄了一段精彩的口播视频"
    result = rule_break_lines(line, max_chars=10)
    assert result.split("\n") == [
        "使用 iPhone 15",
        "拍摄了一段精彩的口播视频",
    ]


def test_does_not_split_modifier_from_head_word() -> None:
    line = "这是一个非常重要的技术突破"
    result = rule_break_lines(line, max_chars=10)
    assert result == line


def test_short_line_unchanged() -> None:
    line = "大家好"
    assert rule_break_lines(line, max_chars=10) == line


def test_no_hard_cut_when_no_valid_break_point() -> None:
    line = "abcdefghijklmnop"
    assert rule_break_lines(line, max_chars=5) == line


def test_multiline_only_breaks_long_rows() -> None:
    text = "短行\n这是一个非常重要的技术突破"
    result = rule_break_lines(text, max_chars=10)
    assert result.split("\n") == ["短行", "这是一个非常重要的技术突破"]


def test_rejects_partial_split_that_leaves_overlength_remainder() -> None:
    line = "普通人的生活压力似乎会随之减轻"
    lexicon = BreakLexicon(break_after_chars=frozenset({"的"}))
    assert rule_break_lines(line, max_chars=10, min_chars=4, lexicon=lexicon) == line


def test_balanced_split_prefers_mid_break_over_near_max() -> None:
    """14 chars / max 10 → ideal 7; prefer mid cut over greedy near-full + stub."""
    line = "一二三四五六七八九十甲乙丙丁"
    lexicon = BreakLexicon(break_after_chars=frozenset({"七", "十"}))
    result = rule_break_lines(line, max_chars=10, lexicon=lexicon)
    lines = result.split("\n")
    assert lines == ["一二三四五六七", "八九十甲乙丙丁"]
    assert count_line_chars(lines[0]) == 7
    assert count_line_chars(lines[1]) == 7


def test_balanced_split_first_cut_near_third_for_three_rows() -> None:
    """24 chars / max 10 → 3 rows, ideal first ≈ 8; not blindly pack to 10."""
    line = "一二三四五六七八九十甲乙丙丁戊己庚辛壬癸子丑寅卯"
    lexicon = BreakLexicon(break_after_chars=frozenset({"八", "十", "己"}))
    result = rule_break_lines(line, max_chars=10, lexicon=lexicon)
    lines = result.split("\n")
    assert lines == [
        "一二三四五六七八",
        "九十甲乙丙丁戊己",
        "庚辛壬癸子丑寅卯",
    ]
    assert all(count_line_chars(part) == 8 for part in lines)


def test_rule_break_rejects_segments_shorter_than_min_chars() -> None:
    """Explicit min_chars=4; only break leaving a 3-char stub → no cut."""
    line = "一二三四五六七八九十甲乙丙"  # 13 chars
    lexicon = BreakLexicon(break_after_chars=frozenset({"十"}))
    assert (
        rule_break_lines(line, max_chars=10, lexicon=lexicon, min_chars=4) == line
    )


def test_rule_break_respects_custom_min_chars() -> None:
    """With min_chars=6, a 7|7 split is preferred over near-max when both valid."""
    line = "一二三四五六七八九十甲乙丙丁"
    lexicon = BreakLexicon(break_after_chars=frozenset({"七", "十"}))
    # After 十 leaves right=4 < 6 → invalid; after 七 leaves 7|7 → ok
    result = rule_break_lines(line, max_chars=10, lexicon=lexicon, min_chars=6)
    assert result.split("\n") == ["一二三四五六七", "八九十甲乙丙丁"]


def test_high_frequency_predicate_breaks_before_modal() -> None:
    line = "上游公司的订单和议价能力可能率先提升"
    result = rule_break_lines(line, max_chars=15)
    assert result.split("\n") == [
        "上游公司的订单和议价能力",
        "可能率先提升",
    ]


def test_protected_negative_modal_breaks_as_a_whole() -> None:
    line = "这个方案绝对不可能短期完成任务"
    result = rule_break_lines(line, max_chars=10)
    assert result.split("\n") == [
        "这个方案绝对",
        "不可能短期完成任务",
    ]
