"""Wording shared by the memo and the deck: number formats, driver sentences, SCQA."""

from __future__ import annotations

import math
from dataclasses import dataclass

from decisionpack.run import AnalysisResult
from decisionpack.spec import MetricSpec

DISCLAIMER_OBSERVATIONAL = (
    "This is observational data. Differences between groups are described, not explained; "
    "nothing here shows that one factor caused another."
)

CURRENCY_SYMBOLS = ("$", "£", "€")

LIMITS = [
    "Observational data: groups were not randomly assigned, so gaps are not effects.",
    "Shapley attributions depend on how the metric is split into factors. A different "
    "factorisation gives different numbers.",
    "Segments that stand out are places to look, not causes. The scan corrects p-values for the "
    "number of segments compared, but cannot add information the data does not hold.",
    "Impact estimates rest on assumptions the author wrote down, each with a source; they are not "
    "forecasts.",
    "Intervals come from a bootstrap over rows and describe sampling noise only, not bias.",
]


def fmt_value(x: float, metric: MetricSpec, signed: bool = False) -> str:
    """Format a value of the headline metric, with its unit."""
    if math.isnan(x):
        return "n/a"
    if signed and metric.unit == "%":
        return fmt_gap(x, metric, signed=True)
    sign = "+" if signed and x > 0 else ("-" if x < 0 else "")
    body = f"{abs(x):,.{metric.decimals}f}"
    if metric.unit in CURRENCY_SYMBOLS:
        return f"{sign}{metric.unit}{body}"
    if metric.unit == "%":
        return f"{sign}{abs(x) * 100:,.{metric.decimals}f}%"
    return f"{sign}{body}{(' ' + metric.unit) if metric.unit else ''}"


def fmt_gap(x: float, metric: MetricSpec, signed: bool = False) -> str:
    """Format a difference. A gap between two percentages is in percentage points, not percent."""
    if math.isnan(x):
        return "n/a"
    if metric.unit == "%":
        sign = "+" if signed and x > 0 else ("-" if x < 0 else "")
        return f"{sign}{abs(x) * 100:,.{metric.decimals}f} pp"
    return fmt_value(x, metric, signed=signed)


def pct(x: float, digits: int = 0) -> str:
    return "n/a" if math.isnan(x) else f"{x * 100:.{digits}f}%"


def factor_label(result: AnalysisResult, name: str) -> str:
    for f in result.spec.bridge.factors:
        if f.name == name:
            return f.label or f.name.replace("_", " ")
    return name.replace("_", " ")


def factor_description(result: AnalysisResult, name: str) -> str:
    for f in result.spec.bridge.factors:
        if f.name == name:
            return f.description or ""
    return ""


def top_driver(result: AnalysisResult) -> tuple[str, float]:
    """The factor with the largest Shapley contribution in the direction of the gap."""
    shares = result.shapley.shares()
    name = max(shares, key=lambda k: shares[k] if not math.isnan(shares[k]) else -math.inf)
    return name, shares[name]


def direction_words(result: AnalysisResult) -> tuple[str, str]:
    """('higher'|'lower', 'worse'|'better') for the comparison group against the baseline."""
    higher = result.gap > 0
    worse = higher == result.spec.metric.lower_is_better
    return ("higher" if higher else "lower"), ("worse" if worse else "better")


@dataclass(frozen=True)
class Scqa:
    situation: str
    complication: str
    question: str
    answer: str


def build_scqa(result: AnalysisResult) -> Scqa:
    m, ctx = result.spec.metric, result.spec.context
    higher, worse = direction_words(result)
    a, b = result.baseline_label, result.comparison_label
    lo, hi = result.gap_ci

    situation = ctx.situation or (
        f"{m.label} was {fmt_value(result.metric_a, m)} for {a} and "
        f"{fmt_value(result.metric_b, m)} for {b}."
    )
    complication = ctx.complication or (
        f"The gap between them is {fmt_gap(abs(result.gap), m)} ({result.ratio:.2f}x), "
        f"{higher} for {b}, which is {worse}. The 95% bootstrap interval for the gap is "
        f"{fmt_gap(lo, m, signed=True)} to {fmt_gap(hi, m, signed=True)}."
    )
    question = ctx.question or (
        f"Which part of {m.label.lower()} explains the gap, and what should we do?"
    )

    name, share = top_driver(result)
    sens = result.sensitivity
    spread = ""
    if sens is not None:
        spread = (
            f" Substituting one factor at a time would put it anywhere from "
            f"{pct(sens.min_share[name])} to {pct(sens.max_share[name])}; the Shapley split "
            "averages over every order."
        )
    answer = f"{factor_label(result, name)} accounts for {pct(share)} of the gap.{spread}"
    if result.recommendations:
        top = result.recommendations[0]
        r = top.recommendation
        answer += (
            f" The first recommendation is to {r.title[0].lower() + r.title[1:].rstrip('.')} "
            f"(base impact {top.base:,.0f} {r.impact_unit}; "
            f"range {top.low:,.0f} to {top.high:,.0f})."
        )
    return Scqa(situation, complication, question, answer)


def tree_counts(result: AnalysisResult) -> dict[str, int]:
    counts = {"supported": 0, "refuted": 0, "untested": 0}
    for r in result.tree_results:
        counts[r.status] += 1
    return counts
