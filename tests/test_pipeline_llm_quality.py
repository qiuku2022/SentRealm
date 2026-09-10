"""Tests for LLM break quality gate."""

from __future__ import annotations

from sentrealm_core.pipeline.llm_quality import (
    conservation_ok,
    length_ok,
    llm_quality_diagnose,
    llm_quality_ok,
    min_chars_for,
    quality_ok,
)


def test_min_chars_for_formula() -> None:
    assert min_chars_for(10) == 4
    assert min_chars_for(15) == 5
    assert min_chars_for(5) == 2
    assert min_chars_for(1) == 2
    assert min_chars_for(3) == 2


def test_conservation_ok_joins_trimmed_parts() -> None:
    assert conservation_ok("abcdef", ["abc", "def"]) is True
    assert conservation_ok("  abcdef  ", ["abc", "def"]) is True
    # Space kept inside a part still aligns
    assert conservation_ok("Hello world", ["Hello w", "orld"]) is True


def test_conservation_ok_allows_boundary_space_consumed_by_newline() -> None:
    original = "Hello world今天我们继续聊人工智能"
    parts = ["Hello", "world今天我们继续聊人工智能"]
    assert conservation_ok(original, parts) is True
    assert llm_quality_ok(original, parts) is True


def test_conservation_rejects_mid_space_deletion_without_boundary() -> None:
    original = "Hello world今天我们继续聊人工智能"
    # Gluing across the space without a boundary between matching parts
    assert conservation_ok(original, ["Helloworld今天我们继续聊人工智能"]) is False
    assert conservation_ok(original, ["Hel", "loworld今天我们继续聊人工智能"]) is False


def test_conservation_rejects_reorder_and_duplicate_mismatch() -> None:
    original = "Hello world"
    assert conservation_ok(original, ["world", "Hello"]) is False
    assert conservation_ok("abcabc", ["abc", "abc"]) is True
    assert conservation_ok("abcabc", ["abc", "ab"]) is False


def test_conservation_rejects_rewrite() -> None:
    assert conservation_ok("abcdef", ["abc", "dez"]) is False
    assert conservation_ok("abcdef", ["abc", "de"]) is False
    assert conservation_ok("Hello world", ["Hello", "worlds"]) is False


def test_length_ok_bounds() -> None:
    # max=10 → min=4
    assert length_ok(["一二三四", "五六七八"], max_chars=10) is True
    assert length_ok(["一二三四五六七八九十甲"], max_chars=10) is False  # 11 > 10
    assert length_ok(["一二三"], max_chars=10) is False  # 3 < 4
    assert length_ok(["", "一二三四"], max_chars=10) is False


def test_quality_ok_respects_explicit_min_chars() -> None:
    original = "一二三四五六"
    parts = ["一二三", "四五六"]
    assert quality_ok(original, parts, max_chars=10, min_chars=2) is True
    assert quality_ok(original, parts, max_chars=10, min_chars=4) is False


def test_llm_quality_ok_allows_short_semantic_segments() -> None:
    """LLM gate does not hard-reject parts below rule-break min_chars."""
    original = "而如果加上往届未就业的"
    parts = ["而如果", "加上往届未就业的"]
    assert llm_quality_ok(original, parts) is True


def test_llm_quality_ok_accepts_diagnosis_four_char_head() -> None:
    original = "这意味着普通人的生活压力会随之减轻"
    parts = ["这意味着", "普通人的生活压力会随之减轻"]
    assert conservation_ok(original, parts) is True
    assert llm_quality_ok(original, parts) is True


def test_llm_quality_ok_allows_over_max_if_shorter_than_original() -> None:
    original = "一二三四五六七八九十十一"
    parts = ["一二三四五六", "七八九十十一"]
    assert llm_quality_ok(original, parts) is True


def test_llm_quality_ok_rejects_single_part() -> None:
    original = "一二三四五六七八九十十一"
    assert llm_quality_ok(original, [original]) is False


def test_llm_quality_ok_rejects_no_progress() -> None:
    # Punctuation-only lines have zero countable chars; cannot satisfy progress.
    original = "，，"
    parts = ["，", "，"]
    assert conservation_ok(original, parts) is True
    assert llm_quality_ok(original, parts) is False


def test_llm_quality_ok_rejects_rewrite() -> None:
    original = "一二三四五六七八九十十一"
    assert llm_quality_ok(original, ["一二三四", "五六七八九十X"]) is False


def test_llm_quality_diagnose_codes() -> None:
    original = "一二三四五六七八九十十一"
    assert llm_quality_diagnose(original, []) == "empty"
    assert llm_quality_diagnose(original, [original]) == "not_split"
    assert (
        llm_quality_diagnose(original, ["一二三四", "五六七八九十X"]) == "conservation"
    )
    assert llm_quality_diagnose("，，", ["，", "，"]) == "no_progress"
    assert (
        llm_quality_diagnose(original, ["一二三四", "五六七八", "九十十一"]) is None
    )
def test_llm_quality_diagnose_soft_still_overlength() -> None:
    original = "一二三四五六七八九十十一"
    parts = ["一二三四五六", "七八九十十一"]
    assert llm_quality_diagnose(original, parts) is None
    assert (
        llm_quality_diagnose(original, parts, max_chars=5, min_chars=2)
        == "still_overlength"
    )


def test_llm_quality_diagnose_soft_too_short() -> None:
    original = "是彻底疯狂了绑走"
    parts = ["是", "彻底疯狂了绑走"]
    assert llm_quality_diagnose(original, parts) is None
    assert (
        llm_quality_diagnose(original, parts, max_chars=10, min_chars=5) == "too_short"
    )
