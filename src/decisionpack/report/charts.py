"""SVG charts, written by hand so the package needs no plotting library.

The waterfall shows the baseline value, one step per factor (Shapley contribution) and the
comparison value. The tree shows each hypothesis coloured by whether the data supports it.
"""

from __future__ import annotations

import textwrap
from xml.sax.saxutils import escape

from decisionpack.report.text import factor_label, fmt_value
from decisionpack.run import AnalysisResult

FONT = "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
INK = "#1f2933"
MUTED = "#52606d"
GRID = "#d9e2ec"
BASE_COLOR = "#486581"
ADVERSE = "#c2410c"
FAVOURABLE = "#0f766e"
STATUS_FILL = {"supported": "#d1fae5", "refuted": "#e5e7eb", "untested": "#ffffff"}
STATUS_STROKE = {"supported": "#0f766e", "refuted": "#6b7280", "untested": "#9ca3af"}


def _svg_open(w: int, h: int, title: str, desc: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-labelledby="t d" font-family="{FONT}">',
        f'<title id="t">{escape(title)}</title>',
        f'<desc id="d">{escape(desc)}</desc>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]


def waterfall_levels(result: AnalysisResult) -> list[tuple[str, float, float, float]]:
    """(label, start, end, delta) for baseline, each factor and the comparison."""
    rows = [(result.baseline_label, 0.0, result.metric_a, result.metric_a)]
    level = result.metric_a
    for name in result.shapley.factors:
        delta = result.shapley.attributions[name]
        rows.append((factor_label(result, name), level, level + delta, delta))
        level += delta
    rows.append((result.comparison_label, 0.0, level, level))
    return rows


def waterfall_svg(result: AnalysisResult) -> str:
    m = result.spec.metric
    rows = waterfall_levels(result)
    width, height = 860, 460
    left, right, top, bottom = 70, 20, 60, 150
    plot_w, plot_h = width - left - right, height - top - bottom
    lows = [min(a, b) for _, a, b, _ in rows]
    highs = [max(a, b) for _, a, b, _ in rows]
    vmin, vmax = min(0.0, *lows), max(highs)
    pad = (vmax - vmin) * 0.08 or 1.0
    vmax += pad
    if vmin < 0:
        vmin -= pad

    def y(v: float) -> float:
        return top + plot_h * (1 - (v - vmin) / (vmax - vmin))

    n = len(rows)
    slot = plot_w / n
    bar_w = slot * 0.62
    title = f"{m.label}: {result.baseline_label} to {result.comparison_label}"
    desc = "Waterfall of the gap split by factor (Shapley). " + "; ".join(
        f"{label} {fmt_value(delta, m, signed=True) if 0 < i < n - 1 else fmt_value(end, m)}"
        for i, (label, _, end, delta) in enumerate(rows)
    )
    svg = _svg_open(width, height, title, desc)
    svg.append(
        f'<text x="{left}" y="28" font-size="17" font-weight="600" fill="{INK}">'
        f"{escape(title)}</text>"
    )
    svg.append(
        f'<text x="{left}" y="46" font-size="12" fill="{MUTED}">'
        "Each step is a factor's Shapley contribution; steps sum to the gap.</text>"
    )
    for i in range(5):
        v = vmin + (vmax - vmin) * i / 4
        svg.append(
            f'<line x1="{left}" x2="{width - right}" y1="{y(v):.1f}" y2="{y(v):.1f}" '
            f'stroke="{GRID}"/>'
        )
        svg.append(
            f'<text x="{left - 8}" y="{y(v) + 4:.1f}" font-size="11" text-anchor="end" '
            f'fill="{MUTED}">{escape(fmt_value(v, m))}</text>'
        )

    prev_end: float | None = None
    for i, (label, start, end, delta) in enumerate(rows):
        cx = left + slot * i + slot / 2
        x = cx - bar_w / 2
        is_total = i in (0, n - 1)
        if is_total:
            fill = BASE_COLOR
        else:
            worse = (delta > 0) == m.lower_is_better
            fill = ADVERSE if worse else FAVOURABLE
        y1, y2 = sorted((y(start), y(end)))
        svg.append(
            f'<rect x="{x:.1f}" y="{y1:.1f}" width="{bar_w:.1f}" '
            f'height="{max(y2 - y1, 1.5):.1f}" fill="{fill}"/>'
        )
        if prev_end is not None and not is_total:
            svg.append(
                f'<line x1="{x - (slot - bar_w):.1f}" x2="{x:.1f}" y1="{y(prev_end):.1f}" '
                f'y2="{y(prev_end):.1f}" stroke="{MUTED}" stroke-dasharray="3 3"/>'
            )
        value_text = fmt_value(end, m) if is_total else fmt_value(delta, m, signed=True)
        svg.append(
            f'<text x="{cx:.1f}" y="{y1 - 6:.1f}" font-size="12" font-weight="600" '
            f'text-anchor="middle" fill="{INK}">{escape(value_text)}</text>'
        )
        for j, line in enumerate(textwrap.wrap(label, 18)[:4]):
            svg.append(
                f'<text x="{cx:.1f}" y="{top + plot_h + 18 + 14 * j:.1f}" font-size="11" '
                f'text-anchor="middle" fill="{INK}">{escape(line)}</text>'
            )
        prev_end = end
    svg.append(
        f'<text x="{left}" y="{height - 12}" font-size="11" fill="{MUTED}">'
        f'<tspan fill="{ADVERSE}">Orange</tspan> pushes the metric the wrong way, '
        f'<tspan fill="{FAVOURABLE}">teal</tspan> the right way.</text>'
    )
    svg.append("</svg>")
    return "\n".join(svg)


def tree_svg(result: AnalysisResult) -> str:
    """Hypothesis tree, laid out left to right, coloured by status."""
    if result.tree is None:
        raise ValueError("this analysis has no hypothesis tree")
    status = {r.node_id: r for r in result.tree_results}
    box_w, box_h, gap_x, gap_y = 250, 78, 44, 16

    positions: dict[str, tuple[int, float]] = {}
    next_row = 0.0

    def place(node, depth: int) -> float:  # type: ignore[no-untyped-def]
        nonlocal next_row
        if not node.children:
            y = next_row
            next_row += 1
        else:
            ys = [place(c, depth + 1) for c in node.children]
            y = sum(ys) / len(ys)
        positions[node.id] = (depth, y)
        return y

    place(result.tree, 0)
    depth_max = max(d for d, _ in positions.values())
    width = 30 + (depth_max + 1) * (box_w + gap_x)
    height = 70 + next_row * (box_h + gap_y)
    svg = _svg_open(
        int(width),
        int(height),
        "Hypothesis tree",
        "Each box is a hypothesis marked supported, refuted or untested.",
    )
    svg.append(
        f'<text x="20" y="28" font-size="17" font-weight="600" fill="{INK}">Hypothesis tree</text>'
    )
    svg.append(
        f'<text x="20" y="46" font-size="12" fill="{MUTED}">'
        "Green: supported. Grey: refuted. Dashed white: untested.</text>"
    )

    def xy(node_id: str) -> tuple[float, float]:
        d, row = positions[node_id]
        return 20 + d * (box_w + gap_x), 62 + row * (box_h + gap_y)

    for node in result.tree.walk():
        x, yv = xy(node.id)
        for child in node.children:
            cx, cy = xy(child.id)
            svg.append(
                f'<path d="M{x + box_w:.1f} {yv + box_h / 2:.1f} C{x + box_w + gap_x / 2:.1f} '
                f"{yv + box_h / 2:.1f} {cx - gap_x / 2:.1f} {cy + box_h / 2:.1f} {cx:.1f} "
                f'{cy + box_h / 2:.1f}" fill="none" stroke="{GRID}" stroke-width="2"/>'
            )
    for node in result.tree.walk():
        x, yv = xy(node.id)
        res = status[node.id]
        dash = ' stroke-dasharray="5 4"' if res.status == "untested" else ""
        svg.append(
            f'<rect x="{x:.1f}" y="{yv:.1f}" width="{box_w}" height="{box_h}" rx="6" '
            f'fill="{STATUS_FILL[res.status]}" stroke="{STATUS_STROKE[res.status]}" '
            f'stroke-width="1.5"{dash}/>'
        )
        svg.append(
            f'<text x="{x + 10:.1f}" y="{yv + 17:.1f}" font-size="10" font-weight="700" '
            f'fill="{STATUS_STROKE[res.status]}">{res.status.upper()}</text>'
        )
        for j, line in enumerate(textwrap.wrap(node.statement, 40)[:3]):
            svg.append(
                f'<text x="{x + 10:.1f}" y="{yv + 33 + 13 * j:.1f}" font-size="11" '
                f'fill="{INK}">{escape(line)}</text>'
            )
    svg.append("</svg>")
    return "\n".join(svg)
