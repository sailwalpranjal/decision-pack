# decision-pack

[![ci](https://github.com/sailwalpranjal/decision-pack/actions/workflows/ci.yml/badge.svg)](https://github.com/sailwalpranjal/decision-pack/actions/workflows/ci.yml)
[![licence: MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

Give it a metric and a table. It returns an analysis of why two segments differ: the gap split between drivers in a way that does not depend on an arbitrary order, the segments where the gap concentrates, an issue tree whose branches have to add up, sized recommendations with a low, base and high case, and a memo and a deck whose slide titles are full-sentence conclusions. The method is borrowed from consulting-style problem solving: hypothesis trees, MECE structure, 80/20, the pyramid principle, SCQA.

## Who it is for, and the problem

It is for a product manager or analyst who has to explain a metric gap and recommend something. My funnel lab split a cost gap by substituting factors one at a time, and its limits section notes that the answer depends on the order. Measured here: the "98.1% is post-click" headline can land anywhere from 70.8% to 128.5% for the same data. That is not a finding. decision-pack replaces the split with Shapley attribution, which averages over every order and still adds up exactly to the gap, and builds the rest of a decision around it.

It is decision support for analysts, not an oracle. I have not interviewed any users; [the interview plan](docs/research/interview-guide.md) is written and [the findings file](docs/research/findings.md) is empty on purpose.

## What it cannot tell you

- **It does not prove causes.** Data where groups were not randomly assigned shows differences. Every output says so.
- **Shapley attributions depend on the factorisation.** Splitting cost per conversion into CPM, click rate and conversion is a choice. A different split gives different numbers. The tool gives you an order-free answer to the question you asked, not the question you should have asked.
- **A segment that stands out is a place to look.** The scan corrects for how many segments it compared and refuses segments with too little data, but it cannot create information that the data does not hold.
- **Impact estimates are your assumptions.** The tool will not make one up. Each assumption needs a low, base and high value and a source, or the run fails.

## Demo

The output for the three cases is committed, so you can read it without running anything:

| Case | Memo | Deck | Waterfall |
|---|---|---|---|
| Funnel lab: campaign 936 against 1178 | [memo](cases/funnel-lab/pack/memo.md) | [deck.pptx](cases/funnel-lab/pack/deck.pptx) | [svg](cases/funnel-lab/pack/waterfall.svg) |
| Online shoppers: new against returning visitors | [memo](cases/online-shoppers/pack/memo.md) | [deck.pptx](cases/online-shoppers/pack/deck.pptx) | [svg](cases/online-shoppers/pack/waterfall.svg) |
| Online retail: see the case folder | [memo](cases/online-retail/pack/memo.md) | [deck.pptx](cases/online-retail/pack/deck.pptx) | [svg](cases/online-retail/pack/waterfall.svg) |

> Screenshot placeholder. To capture: `decisionpack serve` in one terminal, `cd web && npm run dev` in another, open `http://localhost:3000`, upload `cases/funnel-lab/spec.yaml` (with the tree inlined, see `web/README.md`) and the CSV, wait for the run, and take a 1440x900 screenshot of the waterfall and tree. Save it as `docs/img/web.png`.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate      # Python 3.12 or newer
pip install -e ".[dev]"

decisionpack run cases/funnel-lab/spec.yaml cases/funnel-lab/data/KAG_conversion_data.csv --out pack/
pytest                                                  # the test suite
```

Other commands: `decisionpack check spec.yaml data.csv` validates without writing; `decisionpack serve` starts the API (OpenAPI docs at `/docs`); `docker build -t decision-pack . && docker run -p 8000:8000 decision-pack` does the same in a container. The web page is described in [web/README.md](web/README.md).

## How it works

```
 spec.yaml + data.csv
        |
  core/expr.py      safe formulas (no eval)
        |
  run.py  ---- core/bridge.py     Shapley + sequential attribution of the gap
        |----- core/segments.py   scan, mix and rate effects, Holm/BH, Simpson check
        |----- core/tree.py       YAML hypothesis tree, MECE check, supported/refuted/untested
        |----- core/sizing.py     low/base/high assumptions, sensitivity, ICE/RICE
        |----- core/stats.py      z-test, Wilson, bootstrap, power, SPRT (checked against SciPy)
        v
  report/  memo.md . waterfall.svg . tree.svg . deck.pptx      api/  FastAPI jobs      web/  Next.js page
```

A spec says what to compare (`groups`), what the metric is (`sum(numerator) / sum(denominator)`), how it breaks into factors (`bridge`), which dimensions to scan (`segments`), the hypothesis tree, and the recommendations with their assumptions. See [`cases/funnel-lab/spec.yaml`](cases/funnel-lab/spec.yaml) for a full example. The method is explained module by module, with a worked example, in [docs/consulting-method.md](docs/consulting-method.md).

## Evidence

All of this is reproducible from the repository.

- **Tests.** `pytest` runs 264 tests (measured when this README was written) with 95% line and branch coverage (`pytest --cov`). They include property-based tests (Hypothesis) that check the Shapley attributions sum to the gap and do not change when the factor order changes, and that every statistical function agrees with SciPy or statsmodels. Committed case packs are compared with a fresh run whenever the data file is present.
- **It reproduces the funnel lab.** Campaigns 936 against 1178: $15.81 against $63.83, a $48.02 gap. The old sequential split (CPM -$3.74, CTR +$4.66, conversion +$47.10) and the Shapley split (CPM -$11.08, CTR +$12.62, conversion +$46.48) both sum to $48.02, in `tests/test_bridge.py`.
- **Type-checked and linted.** `mypy` in strict mode and `ruff` are clean.

### Measured

Numbers below were measured on one machine (Windows, Intel Core 8 threads, Python 3.13.6, NumPy 2.5.4, pandas 3.1.0). They will differ elsewhere.

- Full analysis of a **synthetic 1,000,000-row table** (two groups, four funnel factors, three segment dimensions, 47 segments, 1,000 bootstrap resamples): **8.3 to 8.9 seconds** in three runs (7.5 s in an earlier run), peak memory about 822 MB. `python scripts/perf_check.py` reproduces it. Large groups are bootstrapped on 2,000 random blocks of rows instead of row by row, which is what keeps this fast; for independent rows it gives nearly the same interval.

## Limits and known gaps

- The API keeps jobs in memory and evicts the oldest after 100. It is for one user or a demo, not a durable service.
- The bridge needs the factors to rebuild the metric exactly, either as a telescoping product or through an explicit `formula`. Anything else is rejected.
- Exact Shapley is limited to 16 factors (it evaluates 2^n subsets).
- The deck is plain by design (python-pptx gives limited layout control). Charts are native PowerPoint charts for the waterfall, and a table when a level goes negative.
- No one outside me has used it. Whether analysts want a pack rather than a chart is the riskiest assumption in [the PRD](docs/product/PRD.md).

## Product thinking

- [PRD](docs/product/PRD.md), [roadmap](docs/product/ROADMAP.md) (RICE arithmetic), [decision log](docs/DECISIONS.md)
- [Research plan](docs/research/interview-guide.md) and [findings](docs/research/findings.md) (empty until interviews happen)
- [Launch drafts](docs/launch.md), [changelog](CHANGELOG.md), [project board setup](docs/project-board.md), [issue drafts](docs/issues/)
- [Resume bullets](docs/resume-bullets.md) and [keyword map](docs/keywords.md), each tied to a file or command that proves it

## Licence

MIT, see [LICENSE](LICENSE). The case data have their own licences, listed in each case README.
