from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy import stats as sps
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import (
    proportion_confint,
    proportion_effectsize,
    proportions_ztest,
)

from decisionpack.core import stats as ds

counts = st.integers(min_value=1, max_value=50_000)


@st.composite
def two_samples(draw):
    n1, n2 = draw(counts), draw(counts)
    x1 = draw(st.integers(min_value=0, max_value=n1))
    x2 = draw(st.integers(min_value=0, max_value=n2))
    return x1, n1, x2, n2


# ---- two-proportion z-test ----------------------------------------------------------------


@pytest.mark.parametrize(
    "x1,n1,x2,n2",
    [(30, 100, 45, 100), (422, 1694, 1470, 10551), (5, 5000, 9, 5200), (110, 400, 98, 380)],
)
@pytest.mark.parametrize("alt", ["two-sided", "larger", "smaller"])
def test_ztest_matches_statsmodels(x1, n1, x2, n2, alt):
    mine = ds.two_proportion_ztest(x1, n1, x2, n2, alternative=alt)
    # statsmodels tests p1 - p2, so "x2 larger" is its "smaller"
    sm_alt = {"two-sided": "two-sided", "larger": "smaller", "smaller": "larger"}[alt]
    z, p = proportions_ztest([x1, x2], [n1, n2], alternative=sm_alt)
    assert mine.statistic == pytest.approx(-z, rel=1e-9, abs=1e-12)
    assert mine.p_value == pytest.approx(p, rel=1e-9, abs=1e-15)


@settings(max_examples=150, deadline=None)
@given(two_samples())
def test_property_ztest_matches_statsmodels(sample):
    x1, n1, x2, n2 = sample
    if x1 + x2 in (0, n1 + n2):  # pooled variance is zero; both libraries return nan
        with pytest.raises(ValueError):
            ds.two_proportion_ztest(x1, n1, x2, n2)
        return
    mine = ds.two_proportion_ztest(x1, n1, x2, n2)
    z, p = proportions_ztest([x1, x2], [n1, n2])
    assert mine.statistic == pytest.approx(-z, rel=1e-8, abs=1e-10)
    assert mine.p_value == pytest.approx(p, rel=1e-6, abs=1e-12)


def test_ztest_confidence_interval_covers_difference_and_matches_wald():
    r = ds.two_proportion_ztest(120, 400, 150, 410)
    assert r.ci_low < r.diff < r.ci_high
    p1, p2 = 120 / 400, 150 / 410
    se = math.sqrt(p1 * (1 - p1) / 400 + p2 * (1 - p2) / 410)
    z = sps.norm.ppf(0.975)
    assert r.ci_low == pytest.approx(p2 - p1 - z * se)
    assert r.ci_high == pytest.approx(p2 - p1 + z * se)


def test_ztest_unpooled_matches_hand_formula():
    r = ds.two_proportion_ztest(120, 400, 150, 410, pooled=False)
    p1, p2 = 120 / 400, 150 / 410
    se = math.sqrt(p1 * (1 - p1) / 400 + p2 * (1 - p2) / 410)
    assert r.statistic == pytest.approx((p2 - p1) / se)


def test_ztest_validation():
    with pytest.raises(ValueError):
        ds.two_proportion_ztest(5, 0, 1, 10)
    with pytest.raises(ValueError):
        ds.two_proportion_ztest(11, 10, 1, 10)
    with pytest.raises(ValueError):
        ds.two_proportion_ztest(1, 10, 1, 10, alternative="sideways")  # type: ignore[arg-type]


def test_ztest_symmetry_when_samples_swapped():
    a = ds.two_proportion_ztest(30, 100, 45, 120)
    b = ds.two_proportion_ztest(45, 120, 30, 100)
    assert a.statistic == pytest.approx(-b.statistic)
    assert a.p_value == pytest.approx(b.p_value)


# ---- Wilson interval ----------------------------------------------------------------------


@pytest.mark.parametrize("conf", [0.8, 0.9, 0.95, 0.99])
@pytest.mark.parametrize("x,n", [(0, 10), (1, 10), (5, 10), (10, 10), (37, 1200), (999, 1000)])
def test_wilson_matches_statsmodels(x, n, conf):
    lo, hi = ds.wilson_interval(x, n, conf)
    sm_lo, sm_hi = proportion_confint(x, n, alpha=1 - conf, method="wilson")
    assert lo == pytest.approx(sm_lo, abs=1e-12)
    assert hi == pytest.approx(sm_hi, abs=1e-12)


@settings(max_examples=150, deadline=None)
@given(st.integers(1, 100_000).flatmap(lambda n: st.tuples(st.integers(0, n), st.just(n))))
def test_property_wilson_is_valid_interval(sample):
    x, n = sample
    lo, hi = ds.wilson_interval(x, n)
    assert 0.0 <= lo <= x / n <= hi <= 1.0


def test_wilson_validation():
    with pytest.raises(ValueError):
        ds.wilson_interval(1, 0)
    with pytest.raises(ValueError):
        ds.wilson_interval(2, 1)
    with pytest.raises(ValueError):
        ds.wilson_interval(1, 2, conf=1.0)


# ---- bootstrap ----------------------------------------------------------------------------


def test_bootstrap_ci_close_to_analytic_for_the_mean():
    rng = np.random.default_rng(1)
    data = rng.normal(10, 3, size=400)
    lo, hi = ds.bootstrap_ci(data, np.mean, n_boot=4000, seed=7)
    se = data.std(ddof=1) / math.sqrt(len(data))
    t = sps.t.ppf(0.975, len(data) - 1)
    assert lo == pytest.approx(data.mean() - t * se, abs=0.1)
    assert hi == pytest.approx(data.mean() + t * se, abs=0.1)


def test_bootstrap_ci_close_to_scipy():
    rng = np.random.default_rng(2)
    data = rng.exponential(2.0, size=300)
    lo, hi = ds.bootstrap_ci(data, np.median, n_boot=4000, seed=3)
    res = sps.bootstrap((data,), np.median, n_resamples=4000, method="percentile",
                        random_state=3)
    assert lo == pytest.approx(res.confidence_interval.low, abs=0.15)
    assert hi == pytest.approx(res.confidence_interval.high, abs=0.15)


def test_bootstrap_is_reproducible_and_seed_dependent():
    data = np.arange(50, dtype=float)
    a = ds.bootstrap_ci(data, np.mean, n_boot=500, seed=11)
    b = ds.bootstrap_ci(data, np.mean, n_boot=500, seed=11)
    c = ds.bootstrap_ci(data, np.mean, n_boot=500, seed=12)
    assert a == b
    assert a != c


def test_bootstrap_validation():
    with pytest.raises(ValueError):
        ds.bootstrap_ci(np.array([]), np.mean)
    with pytest.raises(ValueError):
        ds.bootstrap_ci(np.array([1.0, 2.0]), np.mean, n_boot=0)


def test_bootstrap_ratio_gap_ci_contains_point_estimate_and_narrows_with_data():
    rng = np.random.default_rng(5)

    def make(n, p):
        den = rng.integers(50, 150, size=n).astype(float)
        num = rng.binomial(den.astype(int), p).astype(float)
        return num, den

    na, da = make(60, 0.10)
    nb, db = make(60, 0.14)
    gap, lo, hi = ds.bootstrap_ratio_gap_ci(na, da, nb, db, n_boot=2000, seed=1)
    assert lo < gap < hi
    assert gap == pytest.approx(nb.sum() / db.sum() - na.sum() / da.sum())
    na2, da2 = make(600, 0.10)
    nb2, db2 = make(600, 0.14)
    _, lo2, hi2 = ds.bootstrap_ratio_gap_ci(na2, da2, nb2, db2, n_boot=2000, seed=1)
    assert (hi2 - lo2) < (hi - lo)


def test_bootstrap_ratio_gap_validation():
    with pytest.raises(ValueError):
        ds.bootstrap_ratio_gap_ci(np.array([1.0]), np.array([1.0, 2.0]), np.array([1.0]),
                                  np.array([1.0]))
    with pytest.raises(ValueError):
        ds.bootstrap_ratio_gap_ci(np.array([1.0]), np.array([0.0]), np.array([1.0]),
                                  np.array([1.0]))


# ---- power and sample size ----------------------------------------------------------------


@pytest.mark.parametrize("p1,p2", [(0.10, 0.12), (0.05, 0.08), (0.30, 0.35), (0.02, 0.03)])
@pytest.mark.parametrize("power", [0.8, 0.9])
def test_arcsine_sample_size_matches_statsmodels(p1, p2, power):
    mine = ds.sample_size_two_proportions(p1, p2, alpha=0.05, power=power, method="arcsine")
    h = proportion_effectsize(p2, p1)
    theirs = NormalIndPower().solve_power(effect_size=h, alpha=0.05, power=power, ratio=1.0)
    assert mine == math.ceil(theirs)


@pytest.mark.parametrize("p1,p2,n", [(0.10, 0.12, 3000), (0.05, 0.08, 800), (0.30, 0.35, 1500)])
def test_arcsine_power_matches_statsmodels(p1, p2, n):
    mine = ds.power_two_proportions(p1, p2, n, alpha=0.05, method="arcsine")
    theirs = NormalIndPower().power(effect_size=proportion_effectsize(p2, p1), nobs1=n,
                                    alpha=0.05, ratio=1.0)
    assert mine == pytest.approx(theirs, rel=1e-9, abs=1e-12)


@pytest.mark.parametrize("p1,p2", [(0.10, 0.12), (0.05, 0.08), (0.30, 0.35)])
def test_normal_and_arcsine_sample_sizes_agree_roughly(p1, p2):
    a = ds.sample_size_two_proportions(p1, p2, method="arcsine")
    b = ds.sample_size_two_proportions(p1, p2, method="normal")
    assert abs(a - b) / a < 0.05


@pytest.mark.parametrize("p1,p2", [(0.10, 0.13), (0.30, 0.36)])
def test_sample_size_achieves_requested_power_by_simulation(p1, p2):
    n = ds.sample_size_two_proportions(p1, p2, alpha=0.05, power=0.8, method="normal")
    rng = np.random.default_rng(0)
    trials, hits = 1500, 0
    for _ in range(trials):
        x1, x2 = rng.binomial(n, p1), rng.binomial(n, p2)
        if x1 + x2 in (0, 2 * n):
            continue
        if ds.two_proportion_ztest(int(x1), n, int(x2), n).p_value < 0.05:
            hits += 1
    assert hits / trials == pytest.approx(0.8, abs=0.04)


@settings(max_examples=100, deadline=None)
@given(st.floats(0.02, 0.9), st.floats(0.01, 0.1))
def test_property_more_data_never_lowers_power(p1, delta):
    p2 = min(p1 + delta, 0.99)
    if p2 <= p1:
        return
    small = ds.power_two_proportions(p1, p2, 200)
    large = ds.power_two_proportions(p1, p2, 2000)
    assert large >= small - 1e-12
    assert 0.0 <= small <= 1.0 and 0.0 <= large <= 1.0


def test_power_validation():
    with pytest.raises(ValueError):
        ds.sample_size_two_proportions(0.1, 0.1)
    with pytest.raises(ValueError):
        ds.sample_size_two_proportions(0.0, 0.1)
    with pytest.raises(ValueError):
        ds.sample_size_two_proportions(0.1, 0.2, power=1.0)
    with pytest.raises(ValueError):
        ds.power_two_proportions(0.1, 0.2, 0)
    with pytest.raises(ValueError):
        ds.power_two_proportions(0.1, 0.2, 10, method="guess")  # type: ignore[arg-type]


# ---- multiple comparisons -----------------------------------------------------------------


@settings(max_examples=200, deadline=None)
@given(st.lists(st.floats(1e-9, 1.0), min_size=1, max_size=60))
def test_property_holm_matches_statsmodels(ps):
    mine = ds.holm_adjust(ps)
    theirs = multipletests(ps, method="holm")[1]
    assert np.allclose(mine, theirs, rtol=1e-9, atol=1e-12)


@settings(max_examples=200, deadline=None)
@given(st.lists(st.floats(1e-9, 1.0), min_size=1, max_size=60))
def test_property_bh_matches_statsmodels(ps):
    mine = ds.benjamini_hochberg_adjust(ps)
    theirs = multipletests(ps, method="fdr_bh")[1]
    assert np.allclose(mine, theirs, rtol=1e-9, atol=1e-12)


@settings(max_examples=150, deadline=None)
@given(st.lists(st.floats(1e-9, 1.0), min_size=1, max_size=40))
def test_property_adjusted_p_values_are_valid(ps):
    for adj in (ds.holm_adjust(ps), ds.benjamini_hochberg_adjust(ps)):
        assert len(adj) == len(ps)
        assert all(a >= p - 1e-12 for a, p in zip(adj, ps, strict=True))
        assert all(0.0 <= a <= 1.0 for a in adj)
    # BH is never more conservative than Holm
    assert all(
        b <= h + 1e-12
        for b, h in zip(ds.benjamini_hochberg_adjust(ps), ds.holm_adjust(ps), strict=True)
    )


def test_holm_hand_example():
    # m = 4: sorted p = .01 .02 .03 .04 -> 0.04, 0.06, 0.06, 0.06 after step-down and monotone fix
    assert ds.holm_adjust([0.04, 0.01, 0.03, 0.02]) == pytest.approx([0.06, 0.04, 0.06, 0.06])


def test_bh_hand_example():
    assert ds.benjamini_hochberg_adjust([0.01, 0.04, 0.03, 0.02]) == pytest.approx(
        [0.04, 0.04, 0.04, 0.04]
    )


def test_multiple_comparison_validation():
    with pytest.raises(ValueError):
        ds.holm_adjust([0.5, 1.5])
    with pytest.raises(ValueError):
        ds.benjamini_hochberg_adjust([-0.1])
    assert ds.holm_adjust([]) == []
    assert ds.benjamini_hochberg_adjust([]) == []


# ---- sequential test ----------------------------------------------------------------------


def test_sprt_boundaries_are_walds():
    r = ds.sprt_bernoulli([1, 0], p0=0.1, p1=0.2, alpha=0.05, beta=0.2)
    assert r.lower_bound == pytest.approx(math.log(0.2 / 0.95))
    assert r.upper_bound == pytest.approx(math.log(0.8 / 0.05))


def test_sprt_stops_for_h1_with_many_successes_and_h0_with_few():
    assert ds.sprt_bernoulli([1] * 40, p0=0.1, p1=0.4).decision == "accept_h1"
    assert ds.sprt_bernoulli([0] * 40, p0=0.1, p1=0.4).decision == "accept_h0"
    assert ds.sprt_bernoulli([1, 0, 0], p0=0.1, p1=0.4).decision == "continue"


def test_sprt_llr_matches_direct_computation():
    obs = [1, 0, 0, 1, 0, 0, 0, 1]
    r = ds.sprt_bernoulli(obs, p0=0.2, p1=0.5, alpha=1e-9, beta=1e-9)  # never stops early
    k, n = sum(obs), len(obs)
    expected = k * math.log(0.5 / 0.2) + (n - k) * math.log(0.5 / 0.8)
    assert r.llr == pytest.approx(expected)
    assert r.n_used == n


def test_sprt_stops_at_first_crossing_and_ignores_the_rest():
    obs = [1] * 30 + [0] * 100
    r = ds.sprt_bernoulli(obs, p0=0.1, p1=0.4)
    assert r.decision == "accept_h1"
    assert r.n_used < 30


def test_sprt_error_rates_by_simulation():
    rng = np.random.default_rng(4)
    alpha, beta, p0, p1 = 0.05, 0.2, 0.10, 0.20
    trials = 800
    false_pos = sum(
        ds.sprt_bernoulli(rng.random(2000) < p0, p0, p1, alpha, beta).decision == "accept_h1"
        for _ in range(trials)
    )
    misses = sum(
        ds.sprt_bernoulli(rng.random(2000) < p1, p0, p1, alpha, beta).decision == "accept_h0"
        for _ in range(trials)
    )
    assert false_pos / trials <= alpha + 0.025
    assert misses / trials <= beta + 0.04


def test_sprt_validation():
    with pytest.raises(ValueError):
        ds.sprt_bernoulli([1], p0=0.3, p1=0.2)
    with pytest.raises(ValueError):
        ds.sprt_bernoulli([1], p0=0.1, p1=0.2, alpha=0.0)
    with pytest.raises(ValueError):
        ds.sprt_bernoulli([2], p0=0.1, p1=0.2)
