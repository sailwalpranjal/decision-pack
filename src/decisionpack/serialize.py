"""Plain-dict form of a result, for JSON files and the API."""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any

from decisionpack.report.charts import waterfall_levels
from decisionpack.run import AnalysisResult


def _clean(value: Any) -> Any:
    """Make a value JSON-safe: NaN and infinity become None."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_clean(v) for v in value]
    return value


def result_to_dict(result: AnalysisResult) -> dict[str, Any]:
    spec = result.spec
    out: dict[str, Any] = {
        "title": spec.title,
        "observational": spec.observational,
        "metric": {
            "name": spec.metric.name,
            "label": spec.metric.label,
            "unit": spec.metric.unit,
            "lower_is_better": spec.metric.lower_is_better,
            "baseline": result.metric_a,
            "comparison": result.metric_b,
            "gap": result.gap,
            "ratio": result.ratio,
            "gap_ci": list(result.gap_ci),
        },
        "groups": {
            "baseline": result.baseline_label,
            "comparison": result.comparison_label,
            "n_baseline": result.n_baseline,
            "n_comparison": result.n_comparison,
        },
        "bridge": {
            "factors": list(result.shapley.factors),
            "baseline_factors": result.factors_a,
            "comparison_factors": result.factors_b,
            "shapley": result.shapley.attributions,
            "shapley_shares": result.shapley.shares(),
            "sequential": result.sequential.attributions,
            "sequential_order": list(result.sequential.order or ()),
            "waterfall": [
                {"label": label, "start": s, "end": e, "delta": d}
                for label, s, e, d in waterfall_levels(result)
            ],
            "order_sensitivity": None
            if result.sensitivity is None
            else {
                "n_orders": result.sensitivity.n_orders,
                "min_share": result.sensitivity.min_share,
                "max_share": result.sensitivity.max_share,
            },
        },
        "segments": None,
        "tree": None,
        "recommendations": [],
        "warnings": list(result.warnings),
    }
    if result.scan is not None:
        scan = result.scan
        out["segments"] = {
            "rate_baseline": scan.rate_a,
            "rate_comparison": scan.rate_b,
            "gap": scan.gap,
            "alpha": scan.alpha,
            "correction": scan.correction,
            "family_size": scan.family_size,
            "rows": [asdict(r) for r in scan.rows],
            "excluded": [asdict(e) for e in scan.excluded],
            "simpson": [asdict(s) for s in scan.simpson],
        }
    if result.tree is not None:
        out["tree"] = {
            "results": [asdict(r) for r in result.tree_results],
            "mece_problems": [asdict(p) for p in result.mece_problems],
        }
    for s in result.recommendations:
        r = s.recommendation
        out["recommendations"].append(
            {
                "rank": s.rank,
                "id": r.id,
                "title": r.title,
                "rationale": r.rationale,
                "impact_unit": r.impact_unit,
                "low": s.low,
                "base": s.base,
                "high": s.high,
                "score": s.score,
                "arithmetic": s.arithmetic,
                "assumptions": [asdict(a) for a in r.assumptions],
                "sensitivity": [asdict(x) for x in s.sensitivity],
                "warnings": s.warnings,
            }
        )
    return _clean(out)  # type: ignore[no-any-return]
