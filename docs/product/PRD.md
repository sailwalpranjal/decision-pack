# PRD: decision-pack

**Status:** Written before the build, then updated as the build went. Sections marked "(proposed)" describe things that have not happened.

## Problem

A product manager or analyst is asked "why is this number 4x worse for segment B than for segment A?" and "what should we do about it?". The usual path is a spreadsheet, a one-off notebook, and a slide deck assembled by hand. Three things go wrong:

1. The split of the gap between drivers is arbitrary. If you substitute factors one at a time, the answer depends on the order you chose. I hit this myself in my funnel lab: the "98.1% of the gap is post-click" headline moves between 70.8% and 128.5% depending on order.
2. Segments are picked by eye, with no control for how many were compared or how little data each has.
3. The recommendation arrives without a size, a range, or a statement of what would change the answer.

## Target user

Primary user: a product manager or product analyst who has a table of events or aggregates and must explain a metric gap to people who will act on it. The secondary user is me, as the first analyst to use it. I have not interviewed anyone yet; the interview plan is in `docs/research/interview-guide.md` and the findings file is empty on purpose.

## Jobs to be done

- When two segments differ on a key metric, I want the gap split into drivers in a way that does not depend on an arbitrary order, so I can say where to look first.
- When I look across age, gender, device and so on, I want the segments where the gap concentrates, ranked, with multiple-comparison control and minimum sizes, so I do not chase noise.
- When I write my recommendation, I want each option sized with a low, base and high case and a visible scoring, so my reader can disagree with an assumption rather than with me.
- When I present, I want a memo and a deck whose titles are conclusions, so a busy reader gets the answer from the titles alone.

## Goals

1. An order-independent driver decomposition whose parts sum exactly to the gap.
2. Statistically sound segment scans and tests, cross-checked against SciPy and statsmodels.
3. Hypothesis trees written in YAML, validated for MECE structure numerically, with each node marked supported, refuted or untested.
4. Sized, prioritised recommendations in which every assumption is an input.
5. A memo, SVG charts and a PPTX deck produced from one spec file.

## Non-goals

- Proving causality. Observational data cannot, and the tool says so in every output.
- Forecasting.
- Inventing assumptions. If sizing needs a number the user did not provide, the run fails with a message naming it.
- Being a BI tool or a dashboard.
- Referring to any consulting firm. The README says "consulting-style method".

## User stories and acceptance criteria

| # | Story | Acceptance criteria |
|---|---|---|
| 1 | As an analyst I can decompose a gap between two segments for a product-of-factors metric. | `shapley_bridge` returns one attribution per factor; they sum to the total gap within 1e-9; the result is identical for every permutation of the factor order |
| 2 | As an analyst I can see the old sequential split next to the Shapley split. | For the funnel case, sequential gives CPM -3.74, CTR +4.66, conversion +47.10 and Shapley gives -11.08, +12.62, +46.48; both sum to $48.02 |
| 3 | As an analyst I can scan segments for where a gap concentrates. | Each segment shows size, rate, gap contribution, adjusted p-value (Holm and Benjamini-Hochberg), and is dropped below a minimum size with the reason shown |
| 4 | As an analyst I am warned about Simpson's paradox. | When the overall direction of a gap reverses within every level of a stratifier, the scan flags it |
| 5 | As a PM I can check that my issue tree adds up. | A node whose children do not reproduce the parent metric within tolerance fails validation, naming the node and the numeric difference |
| 6 | As a PM I see which hypotheses the data supports. | Each node is marked supported, refuted or untested, with the statistic and the threshold used |
| 7 | As a PM I get sized recommendations with uncertainty. | Each recommendation has low, base and high impact, a sensitivity table, and an ICE or RICE score with the arithmetic shown. A recommendation with no stated uncertainty is rejected |
| 8 | As a PM I get a memo and a deck. | The memo opens with an SCQA summary; every slide title is a full sentence; an appendix lists methods and limits |
| 9 | As a developer I can run it from the CLI or an API. | `decisionpack run spec.yaml data.csv --out pack/` writes the pack; the API exposes the same run as an asynchronous job with typed models |

## Success metrics (proposed)

- **North star:** time from "a stakeholder asks why" to a defensible recommendation. Not measured; I would time the first five interview participants on their current method and on decision-pack.
- **Input metrics:** share of runs that finish without a validation error; number of tree nodes marked "untested" per run; share of recommendations with all three of low, base and high filled.
- **Guardrail:** no result without stated uncertainty. This is enforced in code and covered by tests, so it is measurable today.

See `docs/product/ROADMAP.md` for the plan.

## Risks

- **Over-reading attributions.** Shapley values depend on how the metric is factored. Splitting cost per conversion into CPM, CTR and conversion is one choice. The README and every report say this.
- **Observational data.** A segment gap is not an effect. The tool never uses the word "cause" for a result.
- **Small samples.** The segment scan enforces minimum sizes and corrects for multiple comparisons, but cannot create information the data does not hold.
- **No user evidence yet.** The riskiest assumption is that analysts want a pack and not just a chart. The interview guide is built to test that first.
