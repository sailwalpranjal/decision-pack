from __future__ import annotations

import copy
from pathlib import Path

import pandas as pd
import pytest
import yaml

from decisionpack.core.bridge import product_metric, shapley_bridge
from decisionpack.run import AnalysisError, run_analysis
from decisionpack.spec import load_spec, parse_spec

ROOT = Path(__file__).resolve().parents[1]
SHOPPERS = ROOT / "cases" / "online-shoppers"


@pytest.fixture(scope="module")
def shoppers(shoppers_df):
    return run_analysis(load_spec(SHOPPERS / "spec.yaml"), shoppers_df, base_dir=SHOPPERS)


def test_unlabelled_sessions_are_dropped(shoppers, shoppers_df):
    assert len(shoppers_df) == 12359
    assert shoppers.n_rows == 12330
    assert shoppers.n_baseline == 10551 and shoppers.n_comparison == 1694


def test_purchase_rates_match_a_direct_computation(shoppers, shoppers_df):
    labelled = shoppers_df[shoppers_df["Revenue"].notna()]
    ret = labelled[labelled["VisitorType"] == "Returning_Visitor"]
    new = labelled[labelled["VisitorType"] == "New_Visitor"]
    assert shoppers.metric_a == pytest.approx((ret["Revenue"] == True).mean())  # noqa: E712
    assert shoppers.metric_b == pytest.approx((new["Revenue"] == True).mean())  # noqa: E712
    assert shoppers.metric_a == pytest.approx(0.1393, abs=0.0001)
    assert shoppers.metric_b == pytest.approx(0.2491, abs=0.0001)


def test_formula_bridge_sums_to_the_gap_and_finds_the_conversion_step(shoppers):
    assert sum(shoppers.shapley.attributions.values()) == pytest.approx(shoppers.gap, abs=1e-12)
    shares = shoppers.shapley.shares()
    assert max(shares, key=lambda k: shares[k]) == "buy_given_valued"
    assert shares["buy_given_valued"] == pytest.approx(0.714, abs=0.002)
    assert shares["pv_rate"] < 0.05
    assert shoppers.sensitivity is not None
    assert shoppers.sensitivity.n_orders == 6


def test_shapley_with_a_formula_differs_from_the_product_default(shoppers):
    product = shapley_bridge(shoppers.factors_a, shoppers.factors_b, product_metric)
    assert product.attributions != shoppers.shapley.attributions


def test_shoppers_tree_is_exclusive_and_exhaustive_and_statuses_make_sense(shoppers):
    assert shoppers.mece_problems == []
    status = {r.node_id: r.status for r in shoppers.tree_results}
    assert status["via_valued"] == "supported"
    assert status["convert"] == "supported"
    assert status["reach"] == "refuted"  # the two groups reach a valued page equally often
    assert status["via_other"] == "refuted"


def test_shoppers_scan_and_recommendations(shoppers):
    assert shoppers.scan is not None and shoppers.scan.family_size == 33
    assert any(r.significant for r in shoppers.scan.rows)
    assert [s.rank for s in shoppers.recommendations] == [1, 2, 3]
    assert shoppers.recommendations[0].recommendation.id == "R1"


def test_a_formula_that_does_not_reproduce_the_metric_is_rejected(shoppers_df):
    data = yaml.safe_load((SHOPPERS / "spec.yaml").read_text(encoding="utf-8"))
    bad = copy.deepcopy(data)
    bad["bridge"]["formula"] = "pv_rate * buy_given_valued"
    with pytest.raises(AnalysisError, match="does not reproduce"):
        run_analysis(parse_spec(bad), shoppers_df, base_dir=SHOPPERS)


def test_formula_may_only_use_known_names(shoppers_df):
    data = yaml.safe_load((SHOPPERS / "spec.yaml").read_text(encoding="utf-8"))
    bad = copy.deepcopy(data)
    bad["bridge"]["formula"] = "pv_rate * mystery"
    from decisionpack.core.expr import ExpressionError

    with pytest.raises(ExpressionError, match="unknown name"):
        run_analysis(parse_spec(bad), shoppers_df, base_dir=SHOPPERS)


def test_missing_data_columns_are_reported(shoppers_df):
    broken = shoppers_df.drop(columns=["PageValues"])
    with pytest.raises(Exception, match="PageValues"):
        run_analysis(load_spec(SHOPPERS / "spec.yaml"), broken, base_dir=SHOPPERS)


def test_every_case_spec_in_the_repo_parses():
    for spec_path in (ROOT / "cases").glob("*/spec.yaml"):
        load_spec(spec_path)
    assert len(list((ROOT / "cases").glob("*/spec.yaml"))) >= 2


def test_dataframe_input_is_not_mutated(shoppers_df):
    before = shoppers_df.copy()
    run_analysis(load_spec(SHOPPERS / "spec.yaml"), shoppers_df, base_dir=SHOPPERS)
    pd.testing.assert_frame_equal(before, shoppers_df)
