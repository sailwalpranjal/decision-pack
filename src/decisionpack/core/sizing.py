"""Impact sizing and prioritisation.

Every number that goes into a sized recommendation is an *assumption the user wrote down*, with a
low, a base and a high value and a source. Nothing is filled in by the code. A recommendation
without at least one well-formed assumption is rejected, which is how the "no result without
stated uncertainty" rule is enforced.
"""

from __future__ import annotations

import ast
import itertools
import math
from dataclasses import dataclass, field
from typing import Literal

from decisionpack.core.expr import evaluate

MAX_ASSUMPTIONS = 12


class MissingUncertaintyError(ValueError):
    """A recommendation was submitted without the uncertainty the guardrail requires."""


@dataclass(frozen=True)
class Assumption:
    name: str
    low: float
    base: float
    high: float
    source: str


@dataclass(frozen=True)
class Scoring:
    """Inputs for ICE (impact, confidence, ease; each 1-10) or RICE (reach, impact, confidence
    as a fraction, effort in person-weeks). The scores are the author's judgement."""

    method: Literal["ice", "rice"]
    impact: float
    confidence: float
    ease: float | None = None
    reach: float | None = None
    effort: float | None = None


@dataclass(frozen=True)
class Recommendation:
    id: str
    title: str
    rationale: str
    impact_formula: str
    impact_unit: str
    assumptions: tuple[Assumption, ...]
    scoring: Scoring


@dataclass(frozen=True)
class SensitivityRow:
    name: str
    at_low: float
    at_high: float
    swing: float


@dataclass(frozen=True)
class SizedRecommendation:
    recommendation: Recommendation
    low: float
    base: float
    high: float
    sensitivity: list[SensitivityRow]
    score: float
    arithmetic: str
    warnings: list[str] = field(default_factory=list)
    rank: int = 0


def _check_assumptions(assumptions: tuple[Assumption, ...]) -> None:
    if not assumptions:
        raise MissingUncertaintyError(
            "a recommendation needs at least one assumption with a low, base and high value"
        )
    if len(assumptions) > MAX_ASSUMPTIONS:
        raise MissingUncertaintyError(f"at most {MAX_ASSUMPTIONS} assumptions are supported")
    names = [a.name for a in assumptions]
    if len(set(names)) != len(names):
        raise MissingUncertaintyError(f"duplicate assumption names in {names}")
    for a in assumptions:
        if not all(math.isfinite(v) for v in (a.low, a.base, a.high)):
            raise MissingUncertaintyError(f"assumption {a.name!r} has a non-finite value")
        if not a.low <= a.base <= a.high:
            raise MissingUncertaintyError(
                f"assumption {a.name!r} must satisfy low <= base <= high; "
                f"got {a.low}, {a.base}, {a.high}"
            )
        if not a.source.strip():
            raise MissingUncertaintyError(
                f"assumption {a.name!r} needs a source (where does the number come from?)"
            )


def _check_scoring(s: Scoring) -> None:
    if s.method == "ice":
        if s.ease is None:
            raise MissingUncertaintyError("ICE scoring needs ease")
        for label, value in (("impact", s.impact), ("confidence", s.confidence), ("ease", s.ease)):
            if not 1 <= value <= 10:
                raise MissingUncertaintyError(f"ICE {label} must be between 1 and 10; got {value}")
    elif s.method == "rice":
        if s.reach is None:
            raise MissingUncertaintyError("RICE scoring needs reach")
        if s.effort is None or s.effort <= 0:
            raise MissingUncertaintyError("RICE scoring needs a positive effort")
        if not 0 < s.confidence <= 1:
            raise MissingUncertaintyError("RICE confidence is a fraction in (0, 1]")
    else:
        raise MissingUncertaintyError(f"unknown scoring method {s.method!r}")


def _score(s: Scoring) -> tuple[float, str]:
    if s.method == "ice":
        assert s.ease is not None
        value = (s.impact + s.confidence + s.ease) / 3
        return value, f"ICE = ({s.impact:g} + {s.confidence:g} + {s.ease:g}) / 3 = {value:.2f}"
    assert s.reach is not None and s.effort is not None
    value = s.reach * s.impact * s.confidence / s.effort
    return value, (
        f"RICE = {s.reach:g} x {s.impact:g} x {s.confidence:g} / {s.effort:g} = {value:.2f}"
    )


def size(rec: Recommendation) -> SizedRecommendation:
    """Compute low, base and high impact, a sensitivity table and a priority score."""
    _check_assumptions(rec.assumptions)
    _check_scoring(rec.scoring)

    def impact(values: dict[str, float]) -> float:
        return float(evaluate(rec.impact_formula, values))

    base_values = {a.name: a.base for a in rec.assumptions}
    base = impact(base_values)

    warnings: list[str] = []
    try:
        used = {n.id for n in ast.walk(ast.parse(rec.impact_formula, mode="eval"))
                if isinstance(n, ast.Name)}
    except SyntaxError:
        used = set()  # evaluate() below reports the syntax error with a clear message
    for name in base_values:
        if name not in used:
            warnings.append(f"assumption {name!r} is not used in the impact formula")

    # Extremes over every corner of the assumption box. With a formula that rises (or falls)
    # monotonically in each input this is simply all-low and all-high, and it stays correct
    # when a higher input makes the impact smaller.
    corners = itertools.product(*[(a.low, a.high) for a in rec.assumptions])
    results = [
        impact({a.name: v for a, v in zip(rec.assumptions, corner, strict=True)})
        for corner in corners
    ]
    low, high = min(results), max(results)
    low, high = min(low, base), max(high, base)
    if low == base == high:
        warnings.append(
            "the assumptions have no spread, so this impact is a point estimate and says nothing "
            "about uncertainty"
        )

    sensitivity: list[SensitivityRow] = []
    for a in rec.assumptions:
        at_low = impact({**base_values, a.name: a.low})
        at_high = impact({**base_values, a.name: a.high})
        sensitivity.append(SensitivityRow(a.name, at_low, at_high, abs(at_high - at_low)))
    sensitivity.sort(key=lambda r: r.swing, reverse=True)

    score, arithmetic = _score(rec.scoring)
    return SizedRecommendation(rec, low, base, high, sensitivity, score, arithmetic, warnings)


def rank(sized: list[SizedRecommendation]) -> list[SizedRecommendation]:
    """Order by score (highest first), ties broken by base impact, and number them from 1."""
    ordered = sorted(sized, key=lambda s: (-s.score, -s.base, s.recommendation.id))
    return [
        SizedRecommendation(
            s.recommendation, s.low, s.base, s.high, s.sensitivity, s.score, s.arithmetic,
            s.warnings, i,
        )
        for i, s in enumerate(ordered, start=1)
    ]
