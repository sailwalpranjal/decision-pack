from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from decisionpack.core.segments import concentration, scan_segments, simpson_check


def make_frame(rows: list[tuple[str, str, int, int]]) -> pd.DataFrame:
    """rows: (group, segment, successes, trials)"""
    return pd.DataFrame(rows, columns=["grp", "seg", "num", "den"])


# ---- Simpson's paradox, constructed -------------------------------------------------------
# Classic admissions-style data. Group B has the higher rate inside each stratum but the lower
# rate overall, because B sends most of its volume to the hard stratum.
SIMPSON = make_frame(
    [
        ("A", "easy", 81, 87),  # 93.1%
        ("A", "hard", 192, 263),  # 73.0%
        ("B", "easy", 234, 270),  # 86.7%  <- lower than A inside "easy"
        ("B", "hard", 55, 80),  # 68.8%  <- lower than A inside "hard"
    ]
)
def reversal_frame() -> pd.DataFrame:
    # A: easy 0.90 (n=1000), hard 0.20 (n=200)   -> overall 0.7500
    # B: easy 0.95 (n=100),  hard 0.30 (n=1000)  -> overall 0.3636
    # B is better in both strata and worse overall.
    return make_frame(
        [
            ("A", "easy", 900, 1000),
            ("A", "hard", 40, 200),
            ("B", "easy", 95, 100),
            ("B", "hard", 300, 1000),
        ]
    )


def test_simpson_reversal_is_flagged():
    res = simpson_check(reversal_frame(), "grp", "A", "B", "seg", "num", "den")
    assert res.reversed
    assert res.overall_diff < 0  # B is worse overall
    assert all(d > 0 for d in res.stratum_diffs.values())  # but better in every stratum
    assert "reverses" in res.message


def test_no_reversal_when_direction_is_consistent():
    df = make_frame(
        [("A", "s1", 10, 100), ("A", "s2", 20, 100), ("B", "s1", 30, 100), ("B", "s2", 40, 100)]
    )
    res = simpson_check(df, "grp", "A", "B", "seg", "num", "den")
    assert not res.reversed
    assert res.overall_diff > 0 and all(d > 0 for d in res.stratum_diffs.values())


def test_mixed_strata_are_not_a_reversal():
    df = make_frame(
        [("A", "s1", 10, 100), ("A", "s2", 50, 100), ("B", "s1", 30, 100), ("B", "s2", 40, 100)]
    )
    res = simpson_check(df, "grp", "A", "B", "seg", "num", "den")
    assert not res.reversed


def test_small_strata_are_ignored_by_simpson_check():
    df = reversal_frame()
    res = simpson_check(df, "grp", "A", "B", "seg", "num", "den", min_denominator=500)
    assert "easy" not in res.stratum_diffs or res.stratum_diffs.keys() == {"hard"}
    assert not res.reversed  # one valid stratum is not enough to call a reversal


def test_simpson_rejects_bad_columns():
    with pytest.raises(KeyError):
        simpson_check(SIMPSON, "grp", "A", "B", "nope", "num", "den")


# ---- scan ---------------------------------------------------------------------------------


def synthetic(seed: int = 2) -> pd.DataFrame:
    """Two groups, three dimensions. Only seg 'x1' truly differs between groups."""
    rng = np.random.default_rng(seed)
    rows = []
    for grp in ("A", "B"):
        for age in ("18-24", "25-34", "35-44"):
            for sex in ("F", "M"):
                for dev in ("x1", "x2", "x3"):
                    den = int(rng.integers(900, 1100))
                    p = 0.10
                    if grp == "B" and dev == "x1":
                        p = 0.16
                    rows.append((grp, age, sex, dev, int(rng.binomial(den, p)), den))
    return pd.DataFrame(rows, columns=["grp", "age", "sex", "dev", "num", "den"])


def test_scan_finds_the_planted_segment_and_not_noise():
    scan = scan_segments(synthetic(), "grp", "A", "B", ["age", "sex", "dev"], "num", "den",
                         min_denominator=500, alpha=0.05)
    by_dev = {r.value: r for r in scan.rows if r.dimension == "dev"}
    assert by_dev["x1"].significant
    assert not by_dev["x2"].significant and not by_dev["x3"].significant
    assert by_dev["x1"].diff == pytest.approx(0.06, abs=0.012)
    top = scan.rows[0]
    assert (top.dimension, top.value) == ("dev", "x1")
    # the planted effect sits in a third of every age and sex segment, so those show about a
    # third of it; they are real differences, just much smaller than the x1 one
    for r in scan.rows:
        if r.dimension in ("age", "sex"):
            assert r.diff == pytest.approx(0.02, abs=0.012)
            assert abs(r.contribution) < abs(top.contribution)


def test_scan_contributions_sum_to_the_gap_within_each_dimension():
    scan = scan_segments(synthetic(), "grp", "A", "B", ["age", "dev"], "num", "den",
                         min_denominator=1)
    for dim in ("age", "dev"):
        rows = [r for r in scan.rows if r.dimension == dim]
        assert sum(r.contribution for r in rows) == pytest.approx(scan.gap, abs=1e-12)
        for r in rows:
            assert r.contribution == pytest.approx(r.rate_effect + r.mix_effect, abs=1e-12)


def test_scan_overall_rates_are_ratios_of_sums():
    df = synthetic()
    scan = scan_segments(df, "grp", "A", "B", ["dev"], "num", "den", min_denominator=1)
    a, b = df[df.grp == "A"], df[df.grp == "B"]
    assert scan.rate_a == pytest.approx(a.num.sum() / a.den.sum())
    assert scan.rate_b == pytest.approx(b.num.sum() / b.den.sum())
    assert scan.gap == pytest.approx(scan.rate_b - scan.rate_a)


def test_minimum_size_rule_excludes_and_explains():
    df = synthetic()
    tiny = pd.DataFrame([("A", "tiny", "F", "x1", 1, 20), ("B", "tiny", "F", "x1", 5, 20)],
                        columns=df.columns)
    scan = scan_segments(pd.concat([df, tiny]), "grp", "A", "B", ["age"], "num", "den",
                         min_denominator=500)
    assert "tiny" not in {r.value for r in scan.rows}
    reasons = {(e.dimension, e.value): e.reason for e in scan.excluded}
    assert ("age", "tiny") in reasons and "below the minimum" in reasons[("age", "tiny")]


def test_segment_missing_from_one_group_is_excluded():
    df = synthetic()
    only_b = pd.DataFrame([("B", "65+", "F", "x1", 50, 1000)], columns=df.columns)
    scan = scan_segments(pd.concat([df, only_b]), "grp", "A", "B", ["age"], "num", "den",
                         min_denominator=100)
    assert "65+" not in {r.value for r in scan.rows}
    assert any(e.value == "65+" and "one group" in e.reason for e in scan.excluded)


def test_multiple_comparison_adjustment_is_applied_across_the_whole_family():
    scan = scan_segments(synthetic(), "grp", "A", "B", ["age", "sex", "dev"], "num", "den",
                         min_denominator=500)
    assert scan.family_size == len(scan.rows) == 8
    assert all(r.p_holm >= r.p_value - 1e-12 for r in scan.rows)
    assert all(r.p_bh <= r.p_holm + 1e-12 for r in scan.rows)


def test_pure_noise_produces_few_false_discoveries():
    rng = np.random.default_rng(42)
    hits = 0
    runs = 40
    for _ in range(runs):
        rows = []
        for grp in ("A", "B"):
            for seg in range(20):
                den = 2000
                rows.append((grp, f"s{seg}", int(rng.binomial(den, 0.1)), den))
        df = pd.DataFrame(rows, columns=["grp", "seg", "num", "den"])
        scan = scan_segments(df, "grp", "A", "B", ["seg"], "num", "den", min_denominator=100)
        hits += any(r.significant for r in scan.rows)
    # With BH at 5% and no real differences, roughly 5% of runs should find anything at all.
    assert hits / runs <= 0.15


def test_scan_reports_simpson_when_a_stratifier_is_given():
    df = reversal_frame()
    scan = scan_segments(df, "grp", "A", "B", ["seg"], "num", "den", min_denominator=10,
                         simpson_stratifiers=["seg"])
    assert scan.simpson and scan.simpson[0].reversed


def test_scan_input_validation():
    df = synthetic()
    with pytest.raises(KeyError):
        scan_segments(df, "grp", "A", "B", ["nope"], "num", "den")
    with pytest.raises(ValueError, match="baseline"):
        scan_segments(df, "grp", "Z", "B", ["age"], "num", "den")
    bad = df.copy()
    bad.loc[0, "num"] = bad.loc[0, "den"] + 5
    with pytest.raises(ValueError, match="exceeds"):
        scan_segments(bad, "grp", "A", "B", ["age"], "num", "den")
    with pytest.raises(ValueError, match="alpha"):
        scan_segments(df, "grp", "A", "B", ["age"], "num", "den", alpha=2)


def test_missing_dimension_values_are_dropped_with_a_note():
    df = synthetic()
    df.loc[:5, "age"] = None
    scan = scan_segments(df, "grp", "A", "B", ["age"], "num", "den", min_denominator=1)
    assert any("missing" in e.reason for e in scan.excluded)


# ---- 80/20 --------------------------------------------------------------------------------


def test_concentration_picks_the_fewest_segments_covering_the_share():
    scan = scan_segments(synthetic(), "grp", "A", "B", ["dev"], "num", "den",
                         min_denominator=1)
    rows = concentration(scan, "dev", share=0.8)
    assert rows[0].value == "x1"
    covered = sum(abs(r.contribution) for r in rows)
    total = sum(abs(r.contribution) for r in scan.rows if r.dimension == "dev")
    assert covered / total >= 0.8


def test_concentration_unknown_dimension_returns_nothing():
    scan = scan_segments(synthetic(), "grp", "A", "B", ["dev"], "num", "den")
    assert concentration(scan, "age") == []
