"""The packs under cases/*/pack are committed as evidence. These tests keep them honest: they
must be internally consistent, and where the data is available they must be exactly what the
current code produces."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from decisionpack.report.memo import render_memo
from decisionpack.run import run_analysis
from decisionpack.serialize import result_to_dict
from decisionpack.spec import load_spec

ROOT = Path(__file__).resolve().parents[1]
CASES = sorted(p for p in (ROOT / "cases").iterdir() if (p / "spec.yaml").exists())
DATA_FILES = {
    "funnel-lab": ROOT / "cases" / "funnel-lab" / "data" / "KAG_conversion_data.csv",
    "online-shoppers": ROOT
    / "cases"
    / "online-shoppers"
    / "data"
    / "online_shoppers_intention.csv",
    "online-retail": ROOT / "cases" / "online-retail" / "data" / "sales_lines.csv",
}


def pack_json(case: Path) -> dict:
    return json.loads((case / "pack" / "result.json").read_text(encoding="utf-8"))


def test_there_are_three_cases():
    assert [c.name for c in CASES] == ["funnel-lab", "online-retail", "online-shoppers"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_pack_files_exist(case):
    names = {p.name for p in (case / "pack").iterdir()}
    assert {
        "memo.md",
        "result.json",
        "waterfall.svg",
        "tree.svg",
        "deck.pptx",
        "segments.csv",
        "recommendations.csv",
    } <= names
    assert (case / "case-study.md").exists() and (case / "README.md").exists()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_committed_bridge_adds_up_and_states_uncertainty(case):
    data = pack_json(case)
    gap = data["metric"]["gap"]
    assert sum(data["bridge"]["shapley"].values()) == pytest.approx(
        gap, abs=1e-6 * max(1, abs(gap))
    )
    assert sum(data["bridge"]["sequential"].values()) == pytest.approx(
        gap, abs=1e-6 * max(1, abs(gap))
    )
    lo, hi = data["metric"]["gap_ci"]
    assert lo < gap < hi
    for rec in data["recommendations"]:
        assert rec["low"] <= rec["base"] <= rec["high"]
        assert all(a["source"].strip() for a in rec["assumptions"])
    assert data["observational"] is True
    assert data["tree"]["mece_problems"] == []


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_committed_memo_says_what_it_cannot_tell_you(case):
    memo = (case / "pack" / "memo.md").read_text(encoding="utf-8")
    assert "## What this cannot tell you" in memo
    assert "observational" in memo.lower()


def test_retail_headline_numbers_in_the_committed_pack():
    data = pack_json(ROOT / "cases" / "online-retail")
    assert data["metric"]["baseline"] == pytest.approx(490.48, abs=0.005)
    assert data["metric"]["comparison"] == pytest.approx(546.82, abs=0.005)
    shapley = data["bridge"]["shapley"]
    assert shapley["lines_per_invoice"] == pytest.approx(64.09, abs=0.005)
    assert shapley["units_per_line"] == pytest.approx(-56.71, abs=0.005)
    assert shapley["revenue_per_unit"] == pytest.approx(48.96, abs=0.005)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_committed_pack_matches_a_fresh_run_when_the_data_is_present(case):
    data_file = DATA_FILES[case.name]
    if not data_file.exists():
        pytest.skip(f"{data_file.name} is not committed; run cases/{case.name}/prepare.py")
    spec = load_spec(case / "spec.yaml")
    df = pd.read_csv(data_file, low_memory=False)
    fresh = run_analysis(spec, df, base_dir=case)
    committed = pack_json(case)
    now = result_to_dict(fresh)
    assert now["bridge"]["shapley"] == pytest.approx(committed["bridge"]["shapley"], rel=1e-9)
    assert now["metric"]["gap_ci"] == pytest.approx(committed["metric"]["gap_ci"], rel=1e-6)
    assert render_memo(fresh) == (case / "pack" / "memo.md").read_text(encoding="utf-8").replace(
        "\r\n", "\n"
    )
