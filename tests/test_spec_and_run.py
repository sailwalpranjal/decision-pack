from __future__ import annotations

import copy
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from decisionpack.core.stats import bootstrap_ratio_gap_ci
from decisionpack.run import AnalysisError, run_analysis
from decisionpack.spec import SpecError, load_spec, parse_spec

CASE = Path(__file__).resolve().parents[1] / "cases" / "funnel-lab"


@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    return pd.read_csv(CASE / "data" / "KAG_conversion_data.csv")


@pytest.fixture(scope="module")
def spec_dict() -> dict:
    return yaml.safe_load((CASE / "spec.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def result(raw):
    return run_analysis(load_spec(CASE / "spec.yaml"), raw, base_dir=CASE)


# ---- spec ---------------------------------------------------------------------------------


def test_shipped_spec_parses():
    spec = load_spec(CASE / "spec.yaml")
    assert spec.metric.name == "cost_per_approved"
    assert spec.bridge.factors[0].name == "cost_per_impression"
    assert spec.tree_file == "tree.yaml"


def test_unknown_key_is_rejected_with_its_path(spec_dict):
    bad = copy.deepcopy(spec_dict)
    bad["metric"]["colour"] = "red"
    with pytest.raises(SpecError, match=r"metric\.colour"):
        parse_spec(bad)


def test_missing_required_field_is_reported(spec_dict):
    bad = copy.deepcopy(spec_dict)
    del bad["groups"]
    with pytest.raises(SpecError, match="groups"):
        parse_spec(bad)


def test_duplicate_factor_names_rejected(spec_dict):
    bad = copy.deepcopy(spec_dict)
    bad["bridge"]["factors"][1]["name"] = bad["bridge"]["factors"][0]["name"]
    with pytest.raises(SpecError, match="duplicate factor"):
        parse_spec(bad)


def test_tree_and_tree_file_are_exclusive(spec_dict):
    bad = copy.deepcopy(spec_dict)
    bad["tree"] = {"id": "x", "statement": "y"}
    with pytest.raises(SpecError, match="either tree or tree_file"):
        parse_spec(bad)


def test_blank_title_rejected(spec_dict):
    bad = copy.deepcopy(spec_dict)
    bad["title"] = "  "
    with pytest.raises(SpecError, match="title"):
        parse_spec(bad)


def test_non_mapping_and_bad_yaml(tmp_path):
    with pytest.raises(SpecError, match="mapping"):
        parse_spec(["a"])
    p = tmp_path / "s.yaml"
    p.write_text("a: [", encoding="utf-8")
    with pytest.raises(SpecError, match="invalid YAML"):
        load_spec(p)


def test_numeric_bounds_are_enforced(spec_dict):
    bad = copy.deepcopy(spec_dict)
    bad["segments"]["alpha"] = 3
    with pytest.raises(SpecError, match="alpha"):
        parse_spec(bad)
    bad = copy.deepcopy(spec_dict)
    bad["n_boot"] = 5
    with pytest.raises(SpecError, match="n_boot"):
        parse_spec(bad)


# ---- run: the funnel case, end to end ------------------------------------------------------


def test_headline_numbers(result):
    assert result.metric_a == pytest.approx(15.81, abs=0.005)
    assert result.metric_b == pytest.approx(63.83, abs=0.005)
    assert result.gap == pytest.approx(48.02, abs=0.005)
    assert result.ratio == pytest.approx(4.04, abs=0.005)
    lo, hi = result.gap_ci
    assert lo < result.gap < hi


def test_bridge_sums_to_the_gap_for_both_methods(result):
    assert sum(result.shapley.attributions.values()) == pytest.approx(result.gap, abs=1e-9)
    assert sum(result.sequential.attributions.values()) == pytest.approx(result.gap, abs=1e-9)
    assert result.sequential.attributions["cost_per_impression"] == pytest.approx(-3.74, abs=0.005)
    assert result.sequential.attributions["impressions_per_click"] == pytest.approx(4.66, abs=0.005)


def test_four_factor_bridge_has_click_to_enquiry_as_the_main_driver(result):
    shares = result.shapley.shares()
    assert max(shares, key=lambda k: shares[k]) == "clicks_per_enquiry"
    assert shares["clicks_per_enquiry"] == pytest.approx(0.934, abs=0.001)
    assert result.sensitivity is not None and result.sensitivity.n_orders == 24


def test_tree_statuses(result):
    status = {r.node_id: r.status for r in result.tree_results}
    assert status["media"] == "refuted"
    assert status["post_click"] == "supported"
    assert status["enquiry"] == "supported"
    assert status["approval"] == "untested"
    assert result.mece_problems == []


def test_segment_scan_ran_and_set_small_segments_aside(result):
    assert result.scan is not None
    assert result.scan.family_size == len(result.scan.rows) == 8
    assert result.scan.excluded
    assert result.scan_gap_ci is not None and result.scan_gap_ci[1] < result.scan_gap_ci[2]


def test_recommendations_are_ranked_with_uncertainty(result):
    assert [s.rank for s in result.recommendations] == [1, 2, 3]
    for s in result.recommendations:
        assert s.low <= s.base <= s.high
    assert result.recommendations[0].score >= result.recommendations[-1].score


def test_observational_warning_present(result):
    assert any("Observational" in w for w in result.warnings)


def test_run_is_deterministic(raw):
    spec = load_spec(CASE / "spec.yaml")
    a = run_analysis(spec, raw, base_dir=CASE)
    b = run_analysis(spec, raw, base_dir=CASE)
    assert a.gap_ci == b.gap_ci and a.scan_gap_ci == b.scan_gap_ci


# ---- run: errors and options --------------------------------------------------------------


def test_factors_that_do_not_multiply_back_are_rejected(raw, spec_dict):
    bad = copy.deepcopy(spec_dict)
    bad["bridge"]["factors"][1]["numerator"] = "Spent"  # breaks the telescoping product
    with pytest.raises(AnalysisError, match="do not multiply back"):
        run_analysis(parse_spec(bad), raw, base_dir=CASE)


def test_unknown_group_value_lists_what_exists(raw, spec_dict):
    bad = copy.deepcopy(spec_dict)
    bad["groups"]["comparison"] = "nope"
    with pytest.raises(AnalysisError, match="no rows"):
        run_analysis(parse_spec(bad), raw, base_dir=CASE)


def test_missing_group_column(raw, spec_dict):
    bad = copy.deepcopy(spec_dict)
    bad["groups"]["column"] = "nope"
    with pytest.raises(AnalysisError, match="group column"):
        run_analysis(parse_spec(bad), raw, base_dir=CASE)


def test_mixed_scoring_methods_are_rejected(raw, spec_dict):
    bad = copy.deepcopy(spec_dict)
    bad["recommendations"][0]["scoring"] = {
        "method": "rice",
        "reach": 5,
        "impact": 2,
        "confidence": 0.5,
        "effort": 2,
    }
    with pytest.raises(AnalysisError, match="mix ICE and RICE"):
        run_analysis(parse_spec(bad), raw, base_dir=CASE)


def test_derived_columns_and_filter_are_applied(raw, spec_dict):
    spec = copy.deepcopy(spec_dict)
    spec["derived_columns"] = {"is_f": "gender == 'F'"}
    spec["filter"] = "is_f"
    spec["segments"] = None
    spec["tree_file"] = None
    spec["recommendations"] = []
    only_f = run_analysis(parse_spec(spec), raw, base_dir=CASE)
    f = raw[(raw.gender == "F") & raw.xyz_campaign_id.isin([936, 1178])]
    assert only_f.n_rows == len(raw[raw.gender == "F"])
    a = f[f.xyz_campaign_id == 936]
    assert only_f.metric_a == pytest.approx(a.Spent.sum() / a.Approved_Conversion.sum())


def test_constant_expression_is_broadcast(raw, spec_dict):
    spec = copy.deepcopy(spec_dict)
    spec["metric"] = {
        "name": "spend_per_ad_set",
        "label": "Spend per ad set",
        "numerator": "Spent",
        "denominator": "1",
    }
    spec["bridge"] = {
        "factors": [{"name": "spend_per_ad_set", "numerator": "Spent", "denominator": "1"}]
    }
    spec["segments"] = None
    spec["tree_file"] = None
    spec["recommendations"] = []
    r = run_analysis(parse_spec(spec), raw, base_dir=CASE)
    sub = raw[raw.xyz_campaign_id == 936]
    assert r.metric_a == pytest.approx(sub.Spent.sum() / len(sub))


def test_inline_tree_is_supported(raw, spec_dict):
    spec = copy.deepcopy(spec_dict)
    spec["tree_file"] = None
    spec["tree"] = yaml.safe_load((CASE / "tree.yaml").read_text(encoding="utf-8"))
    r = run_analysis(parse_spec(spec), raw, base_dir=CASE)
    assert r.tree is not None and len(r.tree_results) == 6


def test_a_broken_tree_is_reported_not_hidden(raw, spec_dict):
    spec = copy.deepcopy(spec_dict)
    spec["tree_file"] = None
    spec["tree"] = {
        "id": "gap",
        "statement": "x",
        "metric": "cost_per_approved",
        "combine": "product",
        "children": [
            {"id": "media", "statement": "m", "metric": "cost_per_impression"},
            {"id": "appeal", "statement": "a", "metric": "impressions_per_click"},
        ],
    }
    r = run_analysis(parse_spec(spec), raw, base_dir=CASE)
    assert r.mece_problems and r.mece_problems[0].node_id == "gap"
    assert any("do not add up" in w for w in r.warnings)


def test_optional_sections_can_be_omitted(raw, spec_dict):
    spec = copy.deepcopy(spec_dict)
    spec["segments"] = None
    spec["tree_file"] = None
    spec["recommendations"] = []
    r = run_analysis(parse_spec(spec), raw, base_dir=CASE)
    assert r.scan is None and r.tree is None and r.recommendations == []


def test_zero_denominator_is_reported(raw, spec_dict):
    spec = copy.deepcopy(spec_dict)
    spec["metric"]["denominator"] = "Approved_Conversion * 0"
    with pytest.raises(AnalysisError, match="sums to zero"):
        run_analysis(parse_spec(spec), raw, base_dir=CASE)


def test_unknown_segment_dimension(raw, spec_dict):
    spec = copy.deepcopy(spec_dict)
    spec["segments"]["dimensions"] = ["nope"]
    with pytest.raises(AnalysisError, match="not found"):
        run_analysis(parse_spec(spec), raw, base_dir=CASE)


# ---- bootstrap on large groups -------------------------------------------------------------


def test_large_groups_are_blocked_and_still_cover_the_estimate():
    rng = np.random.default_rng(0)
    n = 60_000
    den_a = rng.integers(1, 5, n).astype(float)
    den_b = rng.integers(1, 5, n).astype(float)
    num_a = rng.binomial(den_a.astype(int), 0.10).astype(float)
    num_b = rng.binomial(den_b.astype(int), 0.11).astype(float)
    point, lo, hi = bootstrap_ratio_gap_ci(num_a, den_a, num_b, den_b, n_boot=300, seed=1)
    assert point == pytest.approx(num_b.sum() / den_b.sum() - num_a.sum() / den_a.sum())
    assert lo < point < hi
    assert 0 < hi - lo < 0.03
    assert not math.isnan(lo)
