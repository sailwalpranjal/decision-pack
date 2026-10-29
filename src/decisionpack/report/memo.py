"""The one-page memo, in Markdown. The pyramid principle: answer first, support below."""

from __future__ import annotations

import math

from decisionpack.core.segments import concentration
from decisionpack.report.text import (
    DISCLAIMER_OBSERVATIONAL,
    LIMITS,
    build_scqa,
    factor_description,
    factor_label,
    fmt_value,
    pct,
    top_driver,
    tree_counts,
)
from decisionpack.run import AnalysisResult


def _row(*cells: str) -> str:
    return "| " + " | ".join(cells) + " |"


def render_memo(result: AnalysisResult) -> str:
    spec = result.spec
    m = spec.metric
    scqa = build_scqa(result)
    out: list[str] = []
    add = out.append

    add(f"# {spec.title}")
    add("")
    if spec.observational:
        add(f"*{DISCLAIMER_OBSERVATIONAL}*")
        add("")
    add("## Summary")
    add("")
    add(f"**Situation.** {scqa.situation}")
    add("")
    add(f"**Complication.** {scqa.complication}")
    add("")
    add(f"**Question.** {scqa.question}")
    add("")
    add(f"**Answer.** {scqa.answer}")
    add("")

    # ---- drivers ----
    add("## What drives the gap")
    add("")
    add(
        f"Cost is split into factors that multiply to {m.label.lower()}. Each row shows how much "
        f"of the {fmt_value(abs(result.gap), m)} gap a factor carries."
    )
    add("")
    add(
        _row(
            "Factor",
            result.baseline_label,
            result.comparison_label,
            "Shapley",
            "Share",
            "Sequential",
        )
    )
    add(_row("---", "---:", "---:", "---:", "---:", "---:"))
    shares = result.shapley.shares()
    for name in result.shapley.factors:
        desc = factor_description(result, name)
        add(
            _row(
                factor_label(result, name) + (f" ({desc})" if desc else ""),
                f"{result.factors_a[name]:.4g}",
                f"{result.factors_b[name]:.4g}",
                fmt_value(result.shapley.attributions[name], m, signed=True),
                pct(shares[name], 1),
                fmt_value(result.sequential.attributions[name], m, signed=True),
            )
        )
    add("")
    order = " -> ".join(result.sequential.order or ())
    add(
        f"Sequential substitution used the order {order}. It depends on that order; the Shapley "
        "column averages over every order and does not."
    )
    if result.sensitivity is not None:
        name, _ = top_driver(result)
        add(
            f"For {factor_label(result, name).lower()}, the share ranges from "
            f"{pct(result.sensitivity.min_share[name], 1)} to "
            f"{pct(result.sensitivity.max_share[name], 1)} across the "
            f"{result.sensitivity.n_orders} possible orders."
        )
    add("")

    # ---- segments ----
    if result.scan is not None:
        scan = result.scan
        seg = spec.segments
        assert seg is not None
        add("## Where the gap concentrates")
        add("")
        add(
            f"Rate scanned: {seg.label}. Overall {pct(scan.rate_a, 2)} for {result.baseline_label} "
            f"and {pct(scan.rate_b, 2)} for {result.comparison_label}. "
            f"{scan.family_size} segments were compared; p-values are adjusted "
            f"({scan.correction.upper()}) and a segment needs at least "
            f"{seg.min_denominator:g} in the denominator in each group."
        )
        add("")
        add(
            _row(
                "Segment",
                result.baseline_label,
                result.comparison_label,
                "Contribution",
                "Adj. p",
                "Differs?",
            )
        )
        add(_row("---", "---:", "---:", "---:", "---:", "---"))
        for r in scan.rows[:8]:
            adj = r.p_bh if scan.correction == "bh" else r.p_holm
            add(
                _row(
                    f"{r.dimension} = {r.value}",
                    pct(r.rate_a, 2),
                    pct(r.rate_b, 2),
                    f"{r.contribution * 100:+.2f} pp",
                    f"{adj:.3g}",
                    "yes" if r.significant else "no",
                )
            )
        add("")
        for dim in seg.dimensions:
            top = concentration(scan, dim)
            if top:
                names = ", ".join(r.value for r in top)
                add(
                    f"- {dim}: {len(top)} of {sum(1 for r in scan.rows if r.dimension == dim)} "
                    f"segments carry 80% of the absolute gap ({names})."
                )
        for check in scan.simpson:
            add(f"- {check.message}")
        if scan.excluded:
            add(
                f"- {len(scan.excluded)} segment(s) were set aside (too small, one group only, "
                "missing values or not a rate)."
            )
        add("")

    # ---- tree ----
    if result.tree is not None:
        counts = tree_counts(result)
        add("## What the hypothesis tree says")
        add("")
        add(
            f"The data supports {counts['supported']}, refutes {counts['refuted']} and cannot "
            f"settle {counts['untested']}."
        )
        if result.mece_problems:
            add("")
            for p in result.mece_problems:
                add(f"**Tree problem at `{p.node_id}`:** {p.message}")
        add("")
        for node in result.tree_results:
            add(f"- **{node.status.upper()}** `{node.node_id}`: {node.statement} ({node.detail})")
        add("")

    # ---- recommendations ----
    if result.recommendations:
        add("## Recommendations")
        add("")
        add("Impact is shown as low, base and high. Scores are the author's judgement.")
        add("")
        add(_row("#", "Recommendation", "Base", "Range", "Score"))
        add(_row("---:", "---", "---:", "---:", "---:"))
        for sized in result.recommendations:
            rec = sized.recommendation
            add(
                _row(
                    str(sized.rank),
                    rec.title,
                    f"{sized.base:,.0f}",
                    f"{sized.low:,.0f} to {sized.high:,.0f}",
                    f"{sized.score:.2f}",
                )
            )
        add("")
        for sized in result.recommendations:
            rec = sized.recommendation
            add(f"**{sized.rank}. {rec.title}** ({rec.impact_unit}). {rec.rationale}")
            add(f"- {sized.arithmetic}")
            biggest = sized.sensitivity[0] if sized.sensitivity else None
            if biggest is not None and biggest.swing > 0 and not math.isnan(biggest.swing):
                add(
                    f"- Most sensitive to `{biggest.name}`: {biggest.at_low:,.0f} to "
                    f"{biggest.at_high:,.0f} across its range."
                )
            for a in rec.assumptions:
                add(
                    f"- `{a.name}`: {a.low:g} / {a.base:g} / {a.high:g} (low / base / high). "
                    f"Source: {a.source}."
                )
            add("")

    # ---- limits ----
    add("## What this cannot tell you")
    add("")
    for item in LIMITS:
        add(f"- {item}")
    for note in spec.data_notes:
        add(f"- Data: {note}")
    for w in result.warnings:
        add(f"- Note: {w}")
    add("")
    return "\n".join(out)
