"""Regression coverage for the real finance manuscript that exposed over-splitting."""

from pathlib import Path

from sentrealm_core import Settings, preprocess
from sentrealm_core.pipeline.line_count import count_line_chars

_SAMPLE = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "manuscripts"
    / "finance"
    / "01-interest-rate-cuts.md"
)


def test_finance_sample_avoids_quote_and_particle_fragments() -> None:
    raw = _SAMPLE.read_text(encoding="utf-8")
    body = raw.split("\n\n", 1)[1].strip()
    settings = Settings(preset="custom", max_chars=10, min_chars=5)

    result = preprocess(body, settings)
    lines = result.processed.splitlines()
    short_lines = [line for line in lines if count_line_chars(line) < 5]

    assert lines[0] == "每当降息两个字登上新闻"
    assert "降息" not in lines
    assert "普通人的" not in lines
    assert "资金价格" not in lines
    assert short_lines == ["先看负债"]  # 原文中的完整短句，不是自动误切。
    assert result.line_count < 300
