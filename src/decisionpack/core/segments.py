"""Automatic segment scan: where does the gap between two groups concentrate?

For each dimension (age, device, ...) and each value of it, compare the rate of group B with the
rate of group A, test the difference, and split the segment's share of the overall gap into a
*rate effect* (the segment performs differently) and a *mix effect* (the groups have different
amounts of that segment). Tests are corrected for the number of segments compared, segments with
too little data are set aside with a stated reason, and Simpson's-paradox reversals are flagged.

A segment that stands out is a place to look. It is not a cause: this is observational data.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from decisionpack.core.stats import (
    benjamini_hochberg_adjust,
    holm_adjust,
    two_proportion_ztest,
)

Correction = Literal["bh", "holm"]


@dataclass(frozen=True)
class SegmentRow:
    dimension: str
    value: str
    num_a: float
    den_a: float
    num_b: float
    den_b: float
    rate_a: float
    rate_b: float
    diff: float
    ci_low: float
    ci_high: float
    weight_a: float
    weight_b: float
    rate_effect: float
    mix_effect: float
    contribution: float
    z: float
    p_value: float
    p_holm: float = math.nan
    p_bh: float = math.nan
    significant: bool = False


@dataclass(frozen=True)
class Excluded:
    dimension: str
    value: str
    reason: str


@dataclass(frozen=True)
class SimpsonResult:
    stratifier: str
    overall_diff: float
    stratum_diffs: dict[str, float]
    stratum_weights_a: dict[str, float]
    stratum_weights_b: dict[str, float]
    reversed: bool
    message: str


@dataclass(frozen=True)
class SegmentScan:
    group_col: str
    baseline: str
    comparison: str
    rate_a: float
    rate_b: float
    gap: float
    alpha: float
    correction: str
    family_size: int
    rows: list[SegmentRow]
    excluded: list[Excluded] = field(default_factory=list)
    simpson: list[SimpsonResult] = field(default_factory=list)


def _validate_frame(
    df: pd.DataFrame,
    group_col: str,
    baseline: str,
    comparison: str,
    columns: Sequence[str],
    num_col: str,
    den_col: str,
) -> None:
    for col in (group_col, num_col, den_col, *columns):
        if col not in df.columns:
            raise KeyError(f"column {col!r} not found; columns are {list(df.columns)}")
    groups = set(df[group_col].astype(str))
    if baseline not in groups:
        raise ValueError(f"baseline {baseline!r} not found in {group_col!r}; found {sorted(groups)}")
    if comparison not in groups:
        raise ValueError(
            f"comparison {comparison!r} not found in {group_col!r}; found {sorted(groups)}"
        )
    if (df[num_col] > df[den_col]).any():
        raise ValueError(f"{num_col!r} exceeds {den_col!r} in at least one row")
    if (df[den_col] < 0).any() or (df[num_col] < 0).any():
        raise ValueError("counts must not be negative")


def scan_segments(
    df: pd.DataFrame,
    group_col: str,
    baseline: str,
    comparison: str,
    dimensions: Sequence[str],
    num_col: str,
    den_col: str,
    *,
    min_denominator: float = 100,
    alpha: float = 0.05,
    correction: Correction = "bh",
    simpson_stratifiers: Sequence[str] = (),
) -> SegmentScan:
    """Scan every value of every dimension for where ``comparison`` differs from ``baseline``.

    The rate is ``sum(num_col) / sum(den_col)`` within each group and segment. ``min_denominator``
    is applied to both groups: a segment needs at least that many trials in each.
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1")
    _validate_frame(df, group_col, baseline, comparison, dimensions, num_col, den_col)

    groups = df[group_col].astype(str)
    a_all = df[groups == baseline]
    b_all = df[groups == comparison]
    tot_den_a, tot_den_b = float(a_all[den_col].sum()), float(b_all[den_col].sum())
    if tot_den_a <= 0 or tot_den_b <= 0:
        raise ValueError("each group needs a positive total denominator")
    rate_a = float(a_all[num_col].sum()) / tot_den_a
    rate_b = float(b_all[num_col].sum()) / tot_den_b

    rows: list[SegmentRow] = []
    excluded: list[Excluded] = []
    for dim in dimensions:
        present = df[df[dim].notna()]
        n_missing = len(df) - len(present)
        if n_missing:
            excluded.append(Excluded(dim, "(missing)", f"{n_missing} rows have a missing value"))
        values = sorted(present[dim].astype(str).unique())
        a_dim = a_all[a_all[dim].notna()]
        b_dim = b_all[b_all[dim].notna()]
        a_vals = a_dim[dim].astype(str)
        b_vals = b_dim[dim].astype(str)
        for value in values:
            sa, sb = a_dim[a_vals == value], b_dim[b_vals == value]
            if sa.empty or sb.empty:
                excluded.append(Excluded(dim, value, "present in only one group"))
                continue
            den_a, den_b = float(sa[den_col].sum()), float(sb[den_col].sum())
            num_a, num_b = float(sa[num_col].sum()), float(sb[num_col].sum())
            if den_a < min_denominator or den_b < min_denominator:
                excluded.append(
                    Excluded(
                        dim,
                        value,
                        f"below the minimum denominator of {min_denominator:g} "
                        f"(A={den_a:g}, B={den_b:g})",
                    )
                )
                continue
            r_a, r_b = num_a / den_a, num_b / den_b
            w_a, w_b = den_a / tot_den_a, den_b / tot_den_b
            wbar, rbar = (w_a + w_b) / 2, (r_a + r_b) / 2
            rate_effect = wbar * (r_b - r_a)
            mix_effect = (w_b - w_a) * rbar
            try:
                test = two_proportion_ztest(int(round(num_a)), int(round(den_a)),
                                            int(round(num_b)), int(round(den_b)))
                z, p, lo, hi = test.statistic, test.p_value, test.ci_low, test.ci_high
            except ValueError:  # both groups all-success or all-failure: no evidence of a gap
                z, p, lo, hi = 0.0, 1.0, 0.0, 0.0
            rows.append(
                SegmentRow(dim, value, num_a, den_a, num_b, den_b, r_a, r_b, r_b - r_a, lo, hi,
                           w_a, w_b, rate_effect, mix_effect, rate_effect + mix_effect, z, p)
            )

    p_values = [r.p_value for r in rows]
    holm = holm_adjust(p_values)
    bh = benjamini_hochberg_adjust(p_values)
    chosen = bh if correction == "bh" else holm
    final = [
        SegmentRow(**{**r.__dict__, "p_holm": h, "p_bh": b, "significant": c <= alpha})
        for r, h, b, c in zip(rows, holm, bh, chosen, strict=True)
    ]
    final.sort(key=lambda r: abs(r.contribution), reverse=True)

    simpson = [
        simpson_check(df, group_col, baseline, comparison, s, num_col, den_col,
                      min_denominator=min_denominator)
        for s in simpson_stratifiers
    ]
    return SegmentScan(group_col, baseline, comparison, rate_a, rate_b, rate_b - rate_a, alpha,
                       correction, len(final), final, excluded, simpson)


def simpson_check(
    df: pd.DataFrame,
    group_col: str,
    baseline: str,
    comparison: str,
    stratifier: str,
    num_col: str,
    den_col: str,
    *,
    min_denominator: float = 1,
) -> SimpsonResult:
    """Flag a Simpson's-paradox reversal across the levels of ``stratifier``.

    A reversal means the overall gap points one way while, inside every one of at least two
    well-populated strata, it points the other way. The usual cause is that the two groups have
    very different mixes of strata.
    """
    _validate_frame(df, group_col, baseline, comparison, [stratifier], num_col, den_col)
    groups = df[group_col].astype(str)
    a_all, b_all = df[groups == baseline], df[groups == comparison]
    tot_a, tot_b = float(a_all[den_col].sum()), float(b_all[den_col].sum())
    overall = float(b_all[num_col].sum()) / tot_b - float(a_all[num_col].sum()) / tot_a

    diffs: dict[str, float] = {}
    wa: dict[str, float] = {}
    wb: dict[str, float] = {}
    strata_a = a_all[stratifier].astype(str)
    strata_b = b_all[stratifier].astype(str)
    for level in sorted(set(strata_a) & set(strata_b)):
        sa, sb = a_all[strata_a == level], b_all[strata_b == level]
        da, db = float(sa[den_col].sum()), float(sb[den_col].sum())
        if da < min_denominator or db < min_denominator or da <= 0 or db <= 0:
            continue
        diffs[level] = float(sb[num_col].sum()) / db - float(sa[num_col].sum()) / da
        wa[level], wb[level] = da / tot_a, db / tot_b

    signs = {math.copysign(1.0, d) for d in diffs.values() if d != 0}
    zero_free = all(d != 0 for d in diffs.values())
    reversed_ = (
        len(diffs) >= 2
        and zero_free
        and overall != 0
        and len(signs) == 1
        and signs != {math.copysign(1.0, overall)}
    )
    if reversed_:
        direction = "higher" if overall < 0 else "lower"
        message = (
            f"Simpson's paradox: the overall gap reverses within every level of {stratifier!r}. "
            f"{comparison!r} is {direction} than {baseline!r} inside each level, but the overall "
            "gap points the other way, because the groups have different mixes of levels."
        )
    else:
        message = f"No reversal across {stratifier!r} ({len(diffs)} levels compared)."
    return SimpsonResult(stratifier, overall, diffs, wa, wb, reversed_, message)


def concentration(scan: SegmentScan, dimension: str, share: float = 0.8) -> list[SegmentRow]:
    """The fewest segments of ``dimension`` that together carry ``share`` of the absolute gap."""
    rows = sorted(
        (r for r in scan.rows if r.dimension == dimension),
        key=lambda r: abs(r.contribution),
        reverse=True,
    )
    total = sum(abs(r.contribution) for r in rows)
    if total == 0:
        return []
    chosen: list[SegmentRow] = []
    running = 0.0
    for row in rows:
        chosen.append(row)
        running += abs(row.contribution)
        if running / total >= share:
            break
    return chosen
