"""Run a spec against a table and collect every result in one place."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from decisionpack.core.bridge import (
    Bridge,
    OrderSensitivity,
    order_sensitivity,
    sequential_bridge,
    shapley_bridge,
)
from decisionpack.core.expr import evaluate
from decisionpack.core.segments import SegmentScan, scan_segments
from decisionpack.core.sizing import (
    Assumption,
    Recommendation,
    Scoring,
    SizedRecommendation,
    rank,
    size,
)
from decisionpack.core.stats import bootstrap_ratio_gap_ci
from decisionpack.core.tree import (
    MeceProblem,
    NodeResult,
    TreeNode,
    evaluate_tree,
    load_tree,
    parse_tree,
    validate_mece,
)
from decisionpack.spec import Spec


class AnalysisError(ValueError):
    """The spec and the data do not fit together."""


@dataclass
class AnalysisResult:
    spec: Spec
    n_rows: int
    n_baseline: int
    n_comparison: int
    baseline_label: str
    comparison_label: str
    metric_a: float
    metric_b: float
    gap_ci: tuple[float, float]
    factors_a: dict[str, float]
    factors_b: dict[str, float]
    shapley: Bridge
    sequential: Bridge
    sensitivity: OrderSensitivity | None
    scan: SegmentScan | None = None
    scan_gap_ci: tuple[float, float, float] | None = None
    tree: TreeNode | None = None
    tree_values_a: dict[str, float] = field(default_factory=dict)
    tree_values_b: dict[str, float] = field(default_factory=dict)
    mece_problems: list[MeceProblem] = field(default_factory=list)
    tree_results: list[NodeResult] = field(default_factory=list)
    recommendations: list[SizedRecommendation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def gap(self) -> float:
        return self.metric_b - self.metric_a

    @property
    def ratio(self) -> float:
        return self.metric_b / self.metric_a if self.metric_a else math.nan


def _column_namespace(df: pd.DataFrame) -> dict[str, Any]:
    return {str(c): df[c] for c in df.columns}


def _row_values(df: pd.DataFrame, expression: str) -> NDArray[np.float64]:
    """Evaluate a row-level expression; a constant is broadcast to every row."""
    out = evaluate(expression, _column_namespace(df))
    arr = np.asarray(out, dtype=float)
    if arr.ndim == 0:
        arr = np.full(len(df), float(arr))
    if arr.shape != (len(df),):
        raise AnalysisError(f"expression {expression!r} did not give one value per row")
    return arr


def _ratio_of_sums(df: pd.DataFrame, numerator: str, denominator: str, what: str) -> float:
    num = float(_row_values(df, numerator).sum())
    den = float(_row_values(df, denominator).sum())
    if den == 0:
        raise AnalysisError(f"{what}: the denominator {denominator!r} sums to zero")
    return num / den


def prepare_frame(spec: Spec, df: pd.DataFrame) -> pd.DataFrame:
    """Apply derived columns and the row filter."""
    frame = df.copy()
    for name, expression in spec.derived_columns.items():
        frame[name] = _row_values(frame, expression)
    if spec.filter:
        mask = evaluate(spec.filter, _column_namespace(frame))
        frame = frame[np.asarray(mask, dtype=bool)]
    if spec.groups.column not in frame.columns:
        raise AnalysisError(
            f"group column {spec.groups.column!r} not found; columns are {list(frame.columns)}"
        )
    return frame


def run_analysis(spec: Spec, df: pd.DataFrame, base_dir: Path | None = None) -> AnalysisResult:
    frame = prepare_frame(spec, df)
    groups = frame[spec.groups.column].astype(str)
    a = frame[groups == spec.groups.baseline]
    b = frame[groups == spec.groups.comparison]
    for label, part in ((spec.groups.baseline, a), (spec.groups.comparison, b)):
        if part.empty:
            found = sorted(groups.unique())[:10]
            raise AnalysisError(
                f"no rows for {spec.groups.column} = {label!r}; values include {found}"
            )

    m = spec.metric
    metric_a = _ratio_of_sums(a, m.numerator, m.denominator, "baseline metric")
    metric_b = _ratio_of_sums(b, m.numerator, m.denominator, "comparison metric")

    factors_a = {
        f.name: _ratio_of_sums(a, f.numerator, f.denominator, f"factor {f.name}")
        for f in spec.bridge.factors
    }
    factors_b = {
        f.name: _ratio_of_sums(b, f.numerator, f.denominator, f"factor {f.name}")
        for f in spec.bridge.factors
    }
    for label, factors, metric in (
        ("baseline", factors_a, metric_a),
        ("comparison", factors_b, metric_b),
    ):
        rebuilt = math.prod(factors.values())
        if not math.isclose(rebuilt, metric, rel_tol=1e-6, abs_tol=1e-12):
            raise AnalysisError(
                f"the bridge factors do not multiply back to the metric ({label}): "
                f"{rebuilt:g} against {metric:g}. The factors must telescope, for example "
                "spend/impressions x impressions/clicks x clicks/approved = spend/approved."
            )

    shapley = shapley_bridge(factors_a, factors_b)
    sequential = sequential_bridge(factors_a, factors_b)
    sensitivity = order_sensitivity(factors_a, factors_b) if len(factors_a) <= 8 else None

    point, lo, hi = bootstrap_ratio_gap_ci(
        _row_values(a, m.numerator),
        _row_values(a, m.denominator),
        _row_values(b, m.numerator),
        _row_values(b, m.denominator),
        n_boot=spec.n_boot,
        seed=spec.seed,
    )
    del point

    result = AnalysisResult(
        spec=spec,
        n_rows=len(frame),
        n_baseline=len(a),
        n_comparison=len(b),
        baseline_label=spec.groups.baseline_label or spec.groups.baseline,
        comparison_label=spec.groups.comparison_label or spec.groups.comparison,
        metric_a=metric_a,
        metric_b=metric_b,
        gap_ci=(lo, hi),
        factors_a=factors_a,
        factors_b=factors_b,
        shapley=shapley,
        sequential=sequential,
        sensitivity=sensitivity,
    )

    if spec.observational:
        result.warnings.append(
            "Observational data: the groups were not randomly assigned, so gaps describe "
            "differences, not causes."
        )

    if spec.segments is not None:
        _run_segments(spec, frame, result)
    _run_tree(spec, a, b, result, base_dir)
    _run_recommendations(spec, result)
    return result


def _run_segments(spec: Spec, frame: pd.DataFrame, result: AnalysisResult) -> None:
    seg = spec.segments
    assert seg is not None
    work = frame.copy()
    work["__num"] = _row_values(work, seg.numerator)
    work["__den"] = _row_values(work, seg.denominator)
    for dim in seg.dimensions + seg.simpson_stratifiers:
        if dim not in work.columns:
            raise AnalysisError(f"segment dimension {dim!r} not found in the data")
    work[spec.groups.column] = work[spec.groups.column].astype(str)
    result.scan = scan_segments(
        work,
        spec.groups.column,
        spec.groups.baseline,
        spec.groups.comparison,
        seg.dimensions,
        "__num",
        "__den",
        min_denominator=seg.min_denominator,
        alpha=seg.alpha,
        correction=seg.correction,
        simpson_stratifiers=seg.simpson_stratifiers,
    )
    in_a = work[work[spec.groups.column] == spec.groups.baseline]
    in_b = work[work[spec.groups.column] == spec.groups.comparison]
    result.scan_gap_ci = bootstrap_ratio_gap_ci(
        in_a["__num"],
        in_a["__den"],
        in_b["__num"],
        in_b["__den"],
        n_boot=spec.n_boot,
        seed=spec.seed,
    )
    n_tested = result.scan.family_size
    result.warnings.append(
        f"The segment scan compared {n_tested} segments; p-values are adjusted for that "
        f"({seg.correction.upper()})."
    )
    if result.scan.excluded:
        result.warnings.append(
            f"{len(result.scan.excluded)} segment(s) were set aside; see the scan table."
        )


def _tree_values(spec: Spec, df: pd.DataFrame, factors: Mapping[str, float]) -> dict[str, float]:
    values = dict(factors)
    values[spec.metric.name] = _ratio_of_sums(
        df, spec.metric.numerator, spec.metric.denominator, "metric"
    )
    for name, expression in spec.measures.items():
        values[name] = float(evaluate(expression, _column_namespace(df)))
    return values


def _run_tree(
    spec: Spec, a: pd.DataFrame, b: pd.DataFrame, result: AnalysisResult, base_dir: Path | None
) -> None:
    if spec.tree is not None:
        tree = parse_tree(spec.tree)
    elif spec.tree_file is not None:
        path = Path(spec.tree_file)
        if not path.is_absolute() and base_dir is not None:
            path = base_dir / path
        tree = load_tree(path)
    else:
        return
    va = _tree_values(spec, a, result.factors_a)
    vb = _tree_values(spec, b, result.factors_b)
    result.tree, result.tree_values_a, result.tree_values_b = tree, va, vb
    result.mece_problems = validate_mece(tree, va, vb)
    result.tree_results = evaluate_tree(tree, va, vb)
    if result.mece_problems:
        result.warnings.append(
            f"The hypothesis tree has {len(result.mece_problems)} structural problem(s); "
            "its branches do not add up."
        )


def _run_recommendations(spec: Spec, result: AnalysisResult) -> None:
    methods = {r.scoring.method for r in spec.recommendations}
    if len(methods) > 1:
        raise AnalysisError(
            "recommendations mix ICE and RICE scores, which are on different scales and cannot "
            "be ranked together; use one method for the whole spec"
        )
    sized = []
    for r in spec.recommendations:
        rec = Recommendation(
            id=r.id,
            title=r.title,
            rationale=r.rationale,
            impact_formula=r.impact_formula,
            impact_unit=r.impact_unit,
            assumptions=tuple(
                Assumption(x.name, x.low, x.base, x.high, x.source) for x in r.assumptions
            ),
            scoring=Scoring(**r.scoring.model_dump()),
        )
        sized.append(size(rec))
    result.recommendations = rank(sized)
    for s in result.recommendations:
        for w in s.warnings:
            result.warnings.append(f"{s.recommendation.id}: {w}")
