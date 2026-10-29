from __future__ import annotations

import itertools
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import pytest
from pptx import Presentation

from decisionpack.cli import main as cli_main
from decisionpack.pack import write_pack
from decisionpack.report.charts import tree_svg, waterfall_levels, waterfall_svg
from decisionpack.report.deck import build_deck, slide_titles
from decisionpack.report.memo import render_memo
from decisionpack.report.text import build_scqa, fmt_gap, fmt_value, pct
from decisionpack.run import run_analysis
from decisionpack.serialize import result_to_dict
from decisionpack.spec import MetricSpec, load_spec

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "funnel-lab"
GOLDEN = Path(__file__).parent / "golden"


@pytest.fixture(scope="module")
def result():
    df = pd.read_csv(CASE / "data" / "KAG_conversion_data.csv")
    res = run_analysis(load_spec(CASE / "spec.yaml"), df, base_dir=CASE)
    # The bootstrap intervals are tested elsewhere. Fixing them here keeps the golden file from
    # depending on the random stream of a particular NumPy release.
    res.gap_ci = (40.44, 55.34)
    res.scan_gap_ci = (-0.068, -0.095, -0.048)
    return res


def check_golden(name: str, text: str) -> None:
    path = GOLDEN / name
    if os.environ.get("UPDATE_GOLDEN") == "1":
        GOLDEN.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    expected = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert text == expected, f"output differs from {path}; rerun with UPDATE_GOLDEN=1 if intended"


# ---- memo ---------------------------------------------------------------------------------


def test_memo_matches_golden_file(result):
    check_golden("memo_funnel.md", render_memo(result))


def test_memo_opens_with_the_answer_and_states_limits(result):
    memo = render_memo(result)
    assert memo.index("## Summary") < memo.index("## What drives the gap")
    assert "**Answer.**" in memo and "## What this cannot tell you" in memo
    assert "observational" in memo.lower()
    assert "depend on how the metric is split" in memo


def test_memo_every_recommendation_shows_low_base_high_and_arithmetic(result):
    memo = render_memo(result)
    for s in result.recommendations:
        assert s.arithmetic in memo
        assert f"{s.low:,.0f} to {s.high:,.0f}" in memo
    assert memo.count("(low / base / high)") >= 9


def test_scqa_uses_context_overrides(result):
    from decisionpack.spec import ContextSpec

    spec = result.spec.model_copy(update={"context": ContextSpec(situation="S.", question="Q?")})
    res = type(result)(**{**result.__dict__, "spec": spec})
    scqa = build_scqa(res)
    assert scqa.situation == "S." and scqa.question == "Q?"
    assert "gap" in scqa.complication


def test_number_formats():
    dollars = MetricSpec(name="m", label="Cost", numerator="a", denominator="b", unit="$")
    assert fmt_value(1234.5, dollars) == "$1,234.50"
    assert fmt_value(-3.74, dollars, signed=True) == "-$3.74"
    assert fmt_value(3.74, dollars, signed=True) == "+$3.74"
    pc = MetricSpec(name="m", label="Rate", numerator="a", denominator="b", unit="%")
    assert fmt_value(0.0925, pc) == "9.25%"
    plain = MetricSpec(
        name="m", label="Count", numerator="a", denominator="b", unit="days", decimals=1
    )
    assert fmt_value(2.0, plain) == "2.0 days"
    assert fmt_value(float("nan"), plain) == "n/a"
    assert pct(0.934) == "93%" and pct(0.934, 1) == "93.4%"


# ---- charts -------------------------------------------------------------------------------


def test_waterfall_is_valid_svg_and_shows_the_numbers(result):
    svg = waterfall_svg(result)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert "$15.81" in svg and "$63.83" in svg and "+$44.84" in svg and "-$11.00" in svg
    assert "<title" in svg and "<desc" in svg  # accessible name and description


def test_waterfall_levels_chain_from_baseline_to_comparison(result):
    levels = waterfall_levels(result)
    assert levels[0][2] == pytest.approx(result.metric_a)
    assert levels[-1][2] == pytest.approx(result.metric_b)
    for prev, cur in itertools.pairwise(levels[1:-1]):
        assert cur[1] == pytest.approx(prev[2])


def test_tree_svg_is_valid_and_marks_every_node(result):
    svg = tree_svg(result)
    ET.fromstring(svg)
    for r in result.tree_results:
        assert r.status.upper() in svg
    assert svg.count("<rect") >= len(result.tree_results)


def test_tree_svg_without_a_tree_is_an_error(result):
    res = type(result)(**{**result.__dict__, "tree": None})
    with pytest.raises(ValueError, match="no hypothesis tree"):
        tree_svg(res)


def test_svg_text_is_escaped(result):
    spec = result.spec.model_copy(update={"title": "x"})
    res = type(result)(**{**result.__dict__, "spec": spec, "baseline_label": "A & <B>"})
    svg = waterfall_svg(res)
    ET.fromstring(svg)
    assert "A &amp; &lt;B&gt;" in svg


# ---- deck ---------------------------------------------------------------------------------

VERBS = re.compile(
    r"\b(is|are|was|were|carries|carry|explains|explain|differ|differs|supports|refutes|remain|"
    r"comes|come|has|have|recommend|would|put|use|uses|matter|matters|Switching)\b"
)


def test_every_slide_title_is_a_full_sentence(result):
    titles = slide_titles(result)
    assert len(titles) >= 8
    for t in titles:
        assert t.endswith("."), t
        assert len(t.split()) >= 8, t
        assert t[0].isupper(), t
        assert VERBS.search(t), f"no verb found in: {t}"
        assert ":" not in t[:25], f"label-style title: {t}"


def test_deck_titles_in_the_file_match_slide_titles(tmp_path, result):
    path = tmp_path / "deck.pptx"
    build_deck(result, path)
    prs = Presentation(str(path))
    found = []
    for slide in list(prs.slides)[1:]:  # skip the cover
        first = next(s for s in slide.shapes if s.has_text_frame)
        found.append(first.text_frame.text)
    assert found == slide_titles(result)


def test_deck_has_waterfall_chart_and_appendix(tmp_path, result):
    path = tmp_path / "deck.pptx"
    build_deck(result, path)
    prs = Presentation(str(path))
    assert any(shape.has_chart for slide in prs.slides for shape in slide.shapes)
    last_two = [
        " ".join(s.text_frame.text for s in slide.shapes if s.has_text_frame)
        for slide in list(prs.slides)[-2:]
    ]
    assert "Shapley" in last_two[0] and "bootstrap" in last_two[0]
    assert "Observational" in last_two[1] and "factorisation" in last_two[1]


def test_deck_falls_back_to_a_table_when_a_level_is_negative(tmp_path, result):
    res = type(result)(**{**result.__dict__, "metric_a": -1.0})
    res.shapley = result.shapley
    path = tmp_path / "deck.pptx"
    build_deck(res, path)
    assert path.exists()


# ---- pack, json, cli ----------------------------------------------------------------------


def test_pack_writes_every_file(tmp_path, result):
    written = {p.name for p in write_pack(result, tmp_path / "pack")}
    assert written == {
        "memo.md",
        "result.json",
        "waterfall.svg",
        "tree.svg",
        "segments.csv",
        "recommendations.csv",
        "deck.pptx",
    }


def test_pack_can_skip_the_deck(tmp_path, result):
    written = {p.name for p in write_pack(result, tmp_path, deck=False)}
    assert "deck.pptx" not in written


def test_result_json_is_strict_json_and_carries_uncertainty(result):
    data = result_to_dict(result)
    text = json.dumps(data, allow_nan=False)
    back = json.loads(text)
    assert back["metric"]["gap_ci"] == [40.44, 55.34]
    for rec in back["recommendations"]:
        assert rec["low"] <= rec["base"] <= rec["high"]
    assert back["bridge"]["shapley"].keys() == back["bridge"]["sequential"].keys()
    assert sum(back["bridge"]["shapley"].values()) == pytest.approx(back["metric"]["gap"])


def test_cli_run_writes_a_pack(tmp_path, capsys):
    code = cli_main(
        [
            "run",
            str(CASE / "spec.yaml"),
            str(CASE / "data" / "KAG_conversion_data.csv"),
            "--out",
            str(tmp_path / "out"),
            "--no-deck",
        ]
    )
    assert code == 0
    assert (tmp_path / "out" / "memo.md").exists()
    assert "memo.md" in capsys.readouterr().out


def test_cli_check_reports_ok(capsys):
    data = CASE / "data" / "KAG_conversion_data.csv"
    code = cli_main(["check", str(CASE / "spec.yaml"), str(data)])
    assert code == 0 and "ok:" in capsys.readouterr().out


def test_cli_reports_errors_without_a_traceback(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("title: x\n", encoding="utf-8")
    code = cli_main(
        [
            "run",
            str(bad),
            str(CASE / "data" / "KAG_conversion_data.csv"),
            "--out",
            str(tmp_path / "o"),
        ]
    )
    err = capsys.readouterr().err
    assert code == 2 and err.startswith("error: invalid spec")
    code = cli_main(["run", str(CASE / "spec.yaml"), str(tmp_path / "missing.csv")])
    assert code == 2


def test_cli_requires_a_command():
    with pytest.raises(SystemExit):
        cli_main([])


def test_gap_between_percentages_is_in_percentage_points():
    pc = MetricSpec(name="m", label="Rate", numerator="a", denominator="b", unit="%", decimals=1)
    assert fmt_gap(0.1098, pc) == "11.0 pp"
    assert fmt_gap(-0.021, pc, signed=True) == "-2.1 pp"
    assert fmt_gap(0.021, pc, signed=True) == "+2.1 pp"
    assert fmt_value(0.021, pc, signed=True) == "+2.1 pp"
    dollars = MetricSpec(name="m", label="Cost", numerator="a", denominator="b", unit="$")
    assert fmt_gap(48.02, dollars) == "$48.02"
    assert fmt_gap(float("nan"), pc) == "n/a"
