"""Tests for pipeline step 4: rule-based breaking."""

from __future__ import annotations

from sentrealm_core.pipeline.break_lexicon import BreakLexicon
from sentrealm_core.pipeline.line_count import count_line_chars
from sentrealm_core.pipeline.rule_break import rule_break_lines


def test_golden_sample_a_english_word_boundary() -> None:
    line = "使用 iPhone 15 拍摄口播视频"
    result = rule_break_lines(line, max_chars=10)
    assert result.split("\n") == [
        "使用 iPhone 15",
        "拍摄口播视频",
    ]


def test_golden_sample_b_common_discourse_marker() -> None:
    line = "方案需要调整所以我们明天继续讨论"
    result = rule_break_lines(line, max_chars=10)
    assert result.split("\n") == [
        "方案需要调整所以",
        "我们明天继续讨论",
    ]


def test_default_lexicon_does_not_split_ambiguous_function_words() -> None:
    samples = [
        "这套方法有助于提高所有人的表达能力",
        "他把问题讲得非常清楚大家一下就明白了",
    ]

    for line in samples:
        assert rule_break_lines(line, max_chars=10) == line


def test_short_line_unchanged() -> None:
    line = "大家好"
    assert rule_break_lines(line, max_chars=10) == line


def test_no_hard_cut_when_no_valid_break_point() -> None:
    line = "abcdefghijklmnop"
    assert rule_break_lines(line, max_chars=5) == line


def test_multiline_only_breaks_long_rows() -> None:
    text = "短行\n方案需要调整所以我们明天继续讨论"
    result = rule_break_lines(text, max_chars=10)
    assert result.split("\n") == [
        "短行",
        "方案需要调整所以",
        "我们明天继续讨论",
    ]


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
