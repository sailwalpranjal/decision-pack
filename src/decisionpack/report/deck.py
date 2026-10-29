"""The PPTX deck. Every slide title is a full sentence that states the conclusion of the slide,
so a reader who only reads the titles gets the argument (the pyramid principle)."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.util import Emu, Inches, Pt

from decisionpack.report.charts import waterfall_levels
from decisionpack.report.text import (
    LIMITS,
    build_scqa,
    factor_label,
    fmt_gap,
    fmt_value,
    pct,
    top_driver,
    tree_counts,
)
from decisionpack.run import AnalysisResult

INK = RGBColor(0x1F, 0x29, 0x33)
MUTED = RGBColor(0x52, 0x60, 0x6D)
BLUE = RGBColor(0x48, 0x65, 0x81)
ORANGE = RGBColor(0xC2, 0x41, 0x0C)
TEAL = RGBColor(0x0F, 0x76, 0x6E)

SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)


def slide_titles(result: AnalysisResult) -> list[str]:
    """The sentence titles, in slide order. Exposed so tests can check them."""
    spec, m = result.spec, result.spec.metric
    a, b = result.baseline_label, result.comparison_label
    name, share = top_driver(result)
    label = factor_label(result, name)
    titles = [
        f"{m.label} is {result.ratio:.2f} times {'as high' if result.gap > 0 else 'as low'} "
        f"for {b} as for {a}, and the {label.lower()} factor explains {pct(share)} of the gap.",
    ]
    titles.append(
        f"The {label.lower()} factor carries {pct(share)} of the {fmt_gap(abs(result.gap), m)} "
        "gap while the other factors play smaller or opposing parts."
    )
    if result.sensitivity is not None:
        titles.append(
            f"Switching factors one at a time would put the {label.lower()} factor anywhere "
            f"between {pct(result.sensitivity.min_share[name])} and "
            f"{pct(result.sensitivity.max_share[name])}, "
            "so the deck uses the order-independent Shapley split."
        )
    if result.scan is not None:
        sig = [r for r in result.scan.rows if r.significant]
        seg_dir = "higher" if result.scan.gap > 0 else "lower"
        seg_label = spec.segments.label if spec.segments else "rate"
        titles.append(
            f"The segment scan finds that {len(sig)} of {result.scan.family_size} segments differ "
            f"after correcting for the "
            f"number of comparisons, and the {seg_label} is {seg_dir} for {b} overall."
        )
    if result.tree is not None:
        c = tree_counts(result)
        titles.append(
            f"Of {len(result.tree_results)} hypotheses, the data supports {c['supported']}, "
            f"refutes {c['refuted']} and cannot settle {c['untested']}."
        )
    if result.recommendations:
        top = result.recommendations[0]
        r = top.recommendation
        titles.append(
            f"The first recommendation is to {r.title[0].lower() + r.title[1:].rstrip('.')}, "
            f"with a base impact of {top.base:,.0f} {r.impact_unit} and a range of "
            f"{top.low:,.0f} to {top.high:,.0f}."
        )
    titles.append(
        "Every number in this deck comes from the spec, the data and the methods listed here."
    )
    titles.append("The analysis has limits, and these are the ones that matter for this decision.")
    return titles


def _add_title(slide: Any, text: str) -> None:
    box = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), SLIDE_W - Inches(1.2), Inches(1.2))
    frame = box.text_frame
    frame.word_wrap = True
    p = frame.paragraphs[0]
    p.text = text
    p.font.size = Pt(26)
    p.font.bold = True
    p.font.color.rgb = INK


def _add_bullets(slide: Any, items: list[str], size: int = 16) -> None:
    left, top = Inches(0.6), Inches(1.8)
    width = SLIDE_W - Inches(1.2)
    box = slide.shapes.add_textbox(left, top, width, SLIDE_H - top - Inches(0.5))
    frame = box.text_frame
    frame.word_wrap = True
    for i, text in enumerate(items):
        p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        p.text = text
        p.font.size = Pt(size)
        p.font.color.rgb = INK
        p.space_after = Pt(8)


def _add_table(
    slide: Any,
    header: list[str],
    rows: list[list[str]],
    col_widths: list[float] | None = None,
    size: int = 12,
) -> None:
    top = Inches(1.8)
    width = SLIDE_W - Inches(1.2)
    n_rows = len(rows) + 1
    shape = slide.shapes.add_table(
        n_rows, len(header), Inches(0.6), top, width, Inches(0.4) * n_rows
    )
    table = shape.table
    if col_widths:
        total = sum(col_widths)
        for i, w in enumerate(col_widths):
            table.columns[i].width = Emu(int(width * w / total))
    for c, text in enumerate(header):
        cell = table.cell(0, c)
        cell.text = text
        cell.text_frame.paragraphs[0].font.bold = True
        cell.text_frame.paragraphs[0].font.size = Pt(size)
    for r, row in enumerate(rows, start=1):
        for c, text in enumerate(row):
            cell = table.cell(r, c)
            cell.text = text
            cell.text_frame.paragraphs[0].font.size = Pt(size)


def _add_waterfall(slide: Any, result: AnalysisResult) -> bool:
    """Native stacked-column waterfall. Returns False if a level is negative."""
    levels = waterfall_levels(result)
    if any(min(s, e) < 0 for _, s, e, _ in levels):
        return False
    m = result.spec.metric
    data = CategoryChartData()
    data.categories = [label for label, *_ in levels]
    base, adverse, favourable, total = [], [], [], []
    for i, (_, start, end, delta) in enumerate(levels):
        is_total = i in (0, len(levels) - 1)
        if is_total:
            base.append(0.0)
            total.append(end)
            adverse.append(0.0)
            favourable.append(0.0)
        else:
            base.append(min(start, end))
            total.append(0.0)
            worse = (delta > 0) == m.lower_is_better
            adverse.append(abs(delta) if worse else 0.0)
            favourable.append(0.0 if worse else abs(delta))
    data.add_series("base", base)
    data.add_series("Total", total)
    data.add_series("Pushes the wrong way", adverse)
    data.add_series("Pushes the right way", favourable)
    gframe = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_STACKED,
        Inches(0.6),
        Inches(1.7),
        SLIDE_W - Inches(1.2),
        Inches(5.2),
        data,
    )
    chart = gframe.chart
    chart.has_legend = False
    plot = chart.plots[0]
    plot.gap_width = 60
    colors = [None, BLUE, ORANGE, TEAL]
    for series, color in zip(plot.series, colors, strict=True):
        if color is None:
            series.format.fill.background()
            series.format.line.fill.background()
        else:
            series.format.fill.solid()
            series.format.fill.fore_color.rgb = color
    # value labels on the visible series only
    for idx, series in enumerate(plot.series):
        if idx == 0:
            continue
        for p_idx, value in enumerate(series.values):
            if value:
                point = series.points[p_idx]
                label = point.data_label
                label.has_text_frame = True
                delta = levels[p_idx][3]
                shown = fmt_value(value, m) if idx == 1 else fmt_value(delta, m, signed=True)
                label.text_frame.text = shown
                label.position = XL_LABEL_POSITION.INSIDE_END
                label.text_frame.paragraphs[0].font.size = Pt(12)
                label.text_frame.paragraphs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    return True


def build_deck(result: AnalysisResult, path: str | Path) -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H
    blank = prs.slide_layouts[6]
    spec, m = result.spec, result.spec.metric
    titles = iter(slide_titles(result))
    scqa = build_scqa(result)

    # cover
    s = prs.slides.add_slide(blank)
    box = s.shapes.add_textbox(Inches(0.8), Inches(2.4), SLIDE_W - Inches(1.6), Inches(2.5))
    box.text_frame.word_wrap = True
    p = box.text_frame.paragraphs[0]
    p.text = spec.title
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = INK
    q = box.text_frame.add_paragraph()
    q.text = "Decision pack. Observational analysis; see the limits slide."
    q.font.size = Pt(16)
    q.font.color.rgb = MUTED

    # 1 summary
    s = prs.slides.add_slide(blank)
    _add_title(s, next(titles))
    _add_bullets(
        s,
        [
            f"Situation. {scqa.situation}",
            f"Complication. {scqa.complication}",
            f"Question. {scqa.question}",
            f"Answer. {scqa.answer}",
        ],
        size=15,
    )

    # 2 waterfall
    s = prs.slides.add_slide(blank)
    _add_title(s, next(titles))
    if not _add_waterfall(s, result):
        _add_table(
            s,
            ["Factor", "Contribution"],
            [
                [factor_label(result, n), fmt_value(v, m, signed=True)]
                for n, v in result.shapley.attributions.items()
            ],
        )

    # 3 order sensitivity
    if result.sensitivity is not None:
        s = prs.slides.add_slide(blank)
        _add_title(s, next(titles))
        sens = result.sensitivity
        rows = []
        for n in result.shapley.factors:
            rows.append(
                [
                    factor_label(result, n),
                    fmt_value(result.sequential.attributions[n], m, signed=True),
                    fmt_value(result.shapley.attributions[n], m, signed=True),
                    f"{pct(sens.min_share[n])} to {pct(sens.max_share[n])}",
                ]
            )
        _add_table(
            s,
            ["Factor", "Sequential (as listed)", "Shapley", "Share across all orders"],
            rows,
            col_widths=[4, 2, 2, 3],
        )

    # 4 segments
    if result.scan is not None:
        s = prs.slides.add_slide(blank)
        _add_title(s, next(titles))
        scan = result.scan
        rows = []
        for r in scan.rows[:8]:
            adj = r.p_bh if scan.correction == "bh" else r.p_holm
            rows.append(
                [
                    f"{r.dimension} = {r.value}",
                    pct(r.rate_a, 2),
                    pct(r.rate_b, 2),
                    f"{r.contribution * 100:+.2f} pp",
                    f"{adj:.3g}",
                    "yes" if r.significant else "no",
                ]
            )
        _add_table(
            s,
            [
                "Segment",
                result.baseline_label,
                result.comparison_label,
                "Contribution",
                "Adj. p",
                "Differs?",
            ],
            rows,
            col_widths=[3, 2, 2, 2, 1.5, 1.5],
            size=12,
        )

    # 5 tree
    if result.tree is not None:
        s = prs.slides.add_slide(blank)
        _add_title(s, next(titles))
        rows = [[r.node_id, r.status, r.statement, r.detail] for r in result.tree_results]
        _add_table(
            s,
            ["Node", "Status", "Hypothesis", "Evidence"],
            rows,
            col_widths=[1.4, 1.2, 4, 5],
            size=10,
        )

    # 6 recommendations
    if result.recommendations:
        s = prs.slides.add_slide(blank)
        _add_title(s, next(titles))
        rows = []
        for sized in result.recommendations:
            rec = sized.recommendation
            rows.append(
                [
                    str(sized.rank),
                    rec.title,
                    f"{sized.base:,.0f}",
                    f"{sized.low:,.0f} to {sized.high:,.0f}",
                    sized.arithmetic,
                ]
            )
        _add_table(
            s,
            ["#", "Recommendation", "Base impact", "Range", "Score"],
            rows,
            col_widths=[0.5, 5, 1.5, 2, 4],
            size=11,
        )

    # appendix: methods
    s = prs.slides.add_slide(blank)
    _add_title(s, next(titles))
    _add_bullets(
        s,
        [
            "Driver bridge: Shapley attribution over every ordering of the factors; sequential "
            "substitution is shown for comparison. Both sum exactly to the gap.",
            "Segment scan: two-proportion z-tests per segment, Holm and Benjamini-Hochberg "
            f"adjustment across all {result.scan.family_size if result.scan else 0} segments, "
            "minimum-size rule, mix and rate effects, Simpson's paradox check.",
            "Hypothesis tree: children must reproduce the parent numerically (MECE check); "
            "nodes are supported, refuted or untested from a stated test.",
            "Sizing: low, base and high for every assumption, extremes over all corners, "
            "ICE or RICE with the arithmetic shown.",
            f"Uncertainty: bootstrap over rows ({spec.n_boot} resamples, seed {spec.seed}).",
        ],
        size=15,
    )

    # appendix: limits
    s = prs.slides.add_slide(blank)
    _add_title(s, next(titles))
    items = list(LIMITS) + [f"Data: {n}" for n in spec.data_notes]
    _add_bullets(s, items, size=14)

    if math.isnan(result.metric_a):
        raise ValueError("metric is undefined")
    props = prs.core_properties
    props.title = spec.title
    props.author = "decision-pack"
    props.last_modified_by = "decision-pack"
    props.subject = "Decision pack"
    props.comments = ""
    props.keywords = ""
    props.created = props.modified = datetime.now(UTC).replace(microsecond=0, tzinfo=None)
    prs.save(str(path))
