# Decision log

## ADR-1: Shapley attribution instead of sequential substitution

**Status:** accepted

**Context.** The funnel lab splits a $48.02 gap in cost per approved conversion into CPM, CTR and post-click conversion by substituting one factor at a time. The result depends on the order. With the order CPM, CTR, conversion it gives -$3.74, +$4.66, +$47.10; other orders give conversion shares between 70.8% and 128.5% of the gap.

**Options.**
1. Keep sequential substitution and document the order.
2. Log-mean (LMDI) decomposition for products. Order-free, exact for products, but defined only for positive factors and not obviously generalisable to ratios of sums.
3. Shapley values: average the marginal effect of switching each factor over all orderings. Order-independent, sums exactly to the gap, works for any function of the factors.

**Decision.** Shapley is the default; sequential is available, and reports show both side by side.

**Consequences.** Results no longer depend on order. Cost is O(n!) orderings; for n up to about 8 factors that is fine, and above that the code uses the equivalent subset formula with 2^n terms. Shapley still depends on how the metric is factored, and that is stated in every report. The numbers are less familiar to readers, so the report explains them in one sentence.

## ADR-2: Hypothesis trees live in YAML

**Status:** accepted

**Context.** An issue tree is a structure the analyst thinks about and edits. It should be reviewable in a pull request and usable without writing code.

**Options.** Python objects; a JSON schema; YAML files; a diagram tool.

**Decision.** YAML. Each node has an id, a statement, an optional metric formula, optional children, and an optional test.

**Consequences.** Trees diff cleanly and non-programmers can edit them. The validator must therefore check structure itself: unique ids, formulas that parse, and the MECE rule that children's formula must reproduce the parent's value numerically. A hand-written tree that does not add up fails with the node id and the difference.

## ADR-3: Every recommendation carries uncertainty

**Status:** accepted

**Context.** A single impact number invites false precision, and the guardrail in the PRD is "no result without stated uncertainty".

**Options.** Optional ranges; a single number plus a caveat; required low/base/high.

**Decision.** `Recommendation` requires low, base and high impact (low <= base <= high), a named source for each assumption, and a sensitivity table. Sizing raises an error if any is missing. Assumptions are inputs from the spec; the code does not supply defaults.

**Consequences.** Users must type assumptions they would rather skip, which is the point. Runs fail early instead of producing a confident-looking number. The cost is friction on a first run; the sample specs show the format.

## ADR-4: PPTX output through python-pptx

**Status:** accepted

**Context.** The memo is Markdown, but many decision-makers expect a deck.

**Options.** Markdown-to-slides tools; HTML slides; generate PPTX directly; export PDF only.

**Decision.** python-pptx, with one slide per conclusion, a sentence as the title, a chart or table as the body, and a methods-and-limits appendix.

**Consequences.** The file opens in PowerPoint, Keynote and Google Slides, and can be edited. python-pptx gives limited layout control, so the design is plain on purpose. Charts are embedded as images rendered from the SVGs. Slide titles are tested to be complete sentences (they end in a full stop and contain a verb-like word), which is a heuristic and not proof of good writing.

## ADR-5: Pure Python statistics with SciPy and statsmodels as test oracles

**Status:** accepted

**Context.** I want to understand and control every formula, and also not to be wrong.

**Options.** Call SciPy and statsmodels directly; implement the formulas and compare against them in tests.

**Decision.** Implement the functions in `core/stats.py` with NumPy and the standard library for the arithmetic, and cross-check each one in tests against SciPy or statsmodels.

**Consequences.** Fewer runtime dependencies and clear code, with an external check on every function. The tests need SciPy and statsmodels installed (dev dependencies only).
