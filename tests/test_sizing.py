from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from decisionpack.core.expr import ExpressionError
from decisionpack.core.sizing import (
    Assumption,
    MissingUncertaintyError,
    Recommendation,
    Scoring,
    rank,
    size,
)


def rec(**overrides) -> Recommendation:
    base = {
        "id": "R1",
        "title": "Shorten the enquiry form",
        "rationale": "Most clicks never become an enquiry.",
        "impact_formula": "clicks * lift * value",
        "impact_unit": "enquiries per month",
        "assumptions": (
            Assumption("clicks", 30_000, 36_000, 40_000, "ad platform export, last 30 days"),
            Assumption("lift", 0.01, 0.02, 0.04, "my judgement; no test run yet"),
            Assumption("value", 1.0, 1.0, 1.0, "one enquiry counts as one"),
        ),
        "scoring": Scoring(method="ice", impact=8, confidence=6, ease=7),
    }
    base.update(overrides)
    return Recommendation(**base)  # type: ignore[arg-type]


def test_low_base_high_come_from_the_assumption_ranges():
    s = size(rec())
    assert s.base == pytest.approx(36_000 * 0.02 * 1.0)
    assert s.low == pytest.approx(30_000 * 0.01)
    assert s.high == pytest.approx(40_000 * 0.04)
    assert s.low <= s.base <= s.high


def test_low_and_high_use_the_extreme_corner_even_when_a_higher_input_hurts():
    r = rec(
        impact_formula="volume / cost",
        assumptions=(
            Assumption("volume", 100, 200, 300, "forecast"),
            Assumption("cost", 2, 4, 8, "quote"),
        ),
    )
    s = size(r)
    assert s.low == pytest.approx(100 / 8)  # low volume, high cost
    assert s.high == pytest.approx(300 / 2)  # high volume, low cost
    assert s.base == pytest.approx(200 / 4)


def test_sensitivity_table_varies_one_assumption_at_a_time_sorted_by_swing():
    s = size(rec())
    by_name = {row.name: row for row in s.sensitivity}
    assert by_name["lift"].at_low == pytest.approx(36_000 * 0.01)
    assert by_name["lift"].at_high == pytest.approx(36_000 * 0.04)
    assert by_name["clicks"].at_low == pytest.approx(30_000 * 0.02)
    assert by_name["value"].swing == pytest.approx(0)
    swings = [row.swing for row in s.sensitivity]
    assert swings == sorted(swings, reverse=True)
    assert s.sensitivity[0].name == "lift"


def test_ice_arithmetic_is_shown():
    s = size(rec(scoring=Scoring(method="ice", impact=8, confidence=6, ease=7)))
    assert s.score == pytest.approx(7.0)
    assert s.arithmetic == "ICE = (8 + 6 + 7) / 3 = 7.00"


def test_rice_arithmetic_is_shown():
    scoring = Scoring(method="rice", reach=6, impact=2, confidence=0.8, effort=1.5)
    s = size(rec(scoring=scoring))
    assert s.score == pytest.approx(6 * 2 * 0.8 / 1.5)
    assert s.arithmetic == "RICE = 6 x 2 x 0.8 / 1.5 = 6.40"


def test_ranking_orders_by_score_then_by_base_impact():
    a = size(rec(id="A", scoring=Scoring(method="ice", impact=5, confidence=5, ease=5)))
    b = size(rec(id="B", scoring=Scoring(method="ice", impact=9, confidence=7, ease=8)))
    c = size(rec(id="C", scoring=Scoring(method="ice", impact=5, confidence=5, ease=5),
                 assumptions=(Assumption("clicks", 1, 2, 3, "x"),
                              Assumption("lift", 1, 2, 3, "x"),
                              Assumption("value", 1, 2, 3, "x"))))
    ranked = rank([a, c, b])
    assert [r.recommendation.id for r in ranked] == ["B", "A", "C"]
    assert [r.rank for r in ranked] == [1, 2, 3]


# ---- the guardrail: no result without stated uncertainty ----------------------------------


def test_recommendation_without_assumptions_is_rejected():
    with pytest.raises(MissingUncertaintyError, match="at least one assumption"):
        size(rec(assumptions=()))


def test_assumption_must_be_ordered():
    with pytest.raises(MissingUncertaintyError, match="low <= base <= high"):
        size(rec(assumptions=(Assumption("clicks", 5, 4, 6, "x"),
                              Assumption("lift", 0.01, 0.02, 0.03, "x"),
                              Assumption("value", 1, 1, 1, "x"))))


def test_assumption_needs_a_source():
    with pytest.raises(MissingUncertaintyError, match="source"):
        size(rec(assumptions=(Assumption("clicks", 1, 2, 3, "  "),
                              Assumption("lift", 0.01, 0.02, 0.03, "x"),
                              Assumption("value", 1, 1, 1, "x"))))


def test_a_point_estimate_masquerading_as_a_range_is_flagged_as_a_warning():
    r = rec(assumptions=(Assumption("clicks", 36_000, 36_000, 36_000, "export"),
                         Assumption("lift", 0.02, 0.02, 0.02, "guess"),
                         Assumption("value", 1, 1, 1, "x")))
    s = size(r)
    assert s.low == s.base == s.high
    assert any("no spread" in w for w in s.warnings)


def test_formula_must_only_use_declared_assumptions():
    with pytest.raises(ExpressionError, match="unknown name"):
        size(rec(impact_formula="clicks * lift * mystery"))


def test_unused_assumption_is_a_warning_not_an_error():
    s = size(rec(impact_formula="clicks * lift"))
    assert any("value" in w and "not used" in w for w in s.warnings)


def test_duplicate_assumption_names_rejected():
    with pytest.raises(MissingUncertaintyError, match="duplicate"):
        size(rec(assumptions=(Assumption("clicks", 1, 2, 3, "x"), Assumption("clicks", 1, 2, 3, "x"),
                              Assumption("lift", 0.01, 0.02, 0.03, "x"),
                              Assumption("value", 1, 1, 1, "x"))))


def test_scoring_validation():
    with pytest.raises(MissingUncertaintyError, match="ease"):
        size(rec(scoring=Scoring(method="ice", impact=5, confidence=5)))
    with pytest.raises(MissingUncertaintyError, match="reach"):
        size(rec(scoring=Scoring(method="rice", impact=5, confidence=0.5, effort=1)))
    with pytest.raises(MissingUncertaintyError, match="effort"):
        size(rec(scoring=Scoring(method="rice", reach=5, impact=5, confidence=0.5, effort=0)))
    with pytest.raises(MissingUncertaintyError, match="between 1 and 10"):
        size(rec(scoring=Scoring(method="ice", impact=11, confidence=5, ease=5)))


@settings(max_examples=100, deadline=None)
@given(
    st.floats(1, 1e4), st.floats(0, 1), st.floats(0, 1), st.floats(0, 1),
)
def test_property_low_base_high_ordered_for_monotone_formulas(volume, a, b, c):
    lo_mid_hi = sorted([a, b, c])
    r = rec(
        impact_formula="clicks * lift",
        assumptions=(
            Assumption("clicks", volume, volume * 1.1, volume * 1.3, "x"),
            Assumption("lift", *lo_mid_hi, "x"),
        ),
    )
    s = size(r)
    assert s.low <= s.base + 1e-9 <= s.high + 2e-9
