"""Command line: ``decisionpack run spec.yaml data.csv --out pack/``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from decisionpack import __version__
from decisionpack.core.expr import ExpressionError
from decisionpack.core.sizing import MissingUncertaintyError
from decisionpack.core.tree import TreeError
from decisionpack.pack import write_pack
from decisionpack.run import AnalysisError, run_analysis
from decisionpack.spec import SpecError, load_spec

EXPECTED_ERRORS = (
    SpecError,
    AnalysisError,
    ExpressionError,
    TreeError,
    MissingUncertaintyError,
    KeyError,
    FileNotFoundError,
    pd.errors.ParserError,
    pd.errors.EmptyDataError,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="decisionpack",
        description="Explain a metric gap: driver bridge, segment scan, hypothesis tree, sized "
        "recommendations, memo and deck.",
    )
    parser.add_argument("--version", action="version", version=f"decisionpack {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="analyse a CSV against a spec and write a pack")
    run.add_argument("spec", type=Path, help="spec YAML file")
    run.add_argument("data", type=Path, help="CSV file")
    run.add_argument("--out", type=Path, default=Path("pack"), help="output folder (default: pack)")
    run.add_argument("--no-deck", action="store_true", help="skip the PPTX deck")

    check = sub.add_parser("check", help="validate a spec against a CSV without writing anything")
    check.add_argument("spec", type=Path)
    check.add_argument("data", type=Path)

    serve = sub.add_parser("serve", help="start the HTTP API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "serve":
        import uvicorn

        uvicorn.run("decisionpack.api.app:app", host=args.host, port=args.port)
        return 0
    try:
        spec = load_spec(args.spec)
        df = pd.read_csv(args.data, low_memory=False)
        result = run_analysis(spec, df, base_dir=args.spec.parent)
        if args.command == "check":
            print(
                f"ok: {result.n_rows} rows, {len(result.shapley.factors)} factors, "
                f"{len(result.recommendations)} recommendations"
            )
            return 0
        written = write_pack(result, args.out, deck=not args.no_deck)
    except EXPECTED_ERRORS as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
