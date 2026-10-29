"""Write a decision pack to a folder."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from decisionpack.report.charts import tree_svg, waterfall_svg
from decisionpack.report.deck import build_deck
from decisionpack.report.memo import render_memo
from decisionpack.run import AnalysisResult
from decisionpack.serialize import result_to_dict

FILES = ("memo.md", "result.json", "waterfall.svg", "deck.pptx")


def write_pack(result: AnalysisResult, out_dir: str | Path, *, deck: bool = True) -> list[Path]:
    """Write memo, result JSON, charts, CSV tables and (optionally) the deck. Returns the paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    def put(name: str, text: str) -> None:
        path = out / name
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)

    put("memo.md", render_memo(result))
    put("result.json", json.dumps(result_to_dict(result), indent=2, sort_keys=False) + "\n")
    put("waterfall.svg", waterfall_svg(result))
    if result.tree is not None:
        put("tree.svg", tree_svg(result))
    if result.scan is not None:
        path = out / "segments.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(
                [
                    "dimension",
                    "value",
                    "rate_baseline",
                    "rate_comparison",
                    "contribution",
                    "p_value",
                    "p_holm",
                    "p_bh",
                    "significant",
                ]
            )
            for row in result.scan.rows:
                w.writerow(
                    [
                        row.dimension,
                        row.value,
                        f"{row.rate_a:.6f}",
                        f"{row.rate_b:.6f}",
                        f"{row.contribution:.6f}",
                        f"{row.p_value:.6g}",
                        f"{row.p_holm:.6g}",
                        f"{row.p_bh:.6g}",
                        row.significant,
                    ]
                )
        written.append(path)
    if result.recommendations:
        path = out / "recommendations.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(
                ["rank", "id", "title", "unit", "low", "base", "high", "score", "arithmetic"]
            )
            for sized in result.recommendations:
                rec = sized.recommendation
                w.writerow(
                    [
                        sized.rank,
                        rec.id,
                        rec.title,
                        rec.impact_unit,
                        f"{sized.low:.2f}",
                        f"{sized.base:.2f}",
                        f"{sized.high:.2f}",
                        f"{sized.score:.2f}",
                        sized.arithmetic,
                    ]
                )
        written.append(path)
    if deck:
        path = out / "deck.pptx"
        build_deck(result, path)
        written.append(path)
    return written
