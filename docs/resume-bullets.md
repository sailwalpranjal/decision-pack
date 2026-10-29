# Resume bullets

Each bullet is Action + what + a measurable result or an artifact, and is followed by the file or command that proves it. If a bullet cannot be proved by something in these repositories it is not here. Paths outside this repository are written as `<repo>/<path>`; the sibling repositories are the funnel lab, AetherScan, SyncState, Appwrite Migration Guard and NitroDB.

Counts were measured when this file was written (264 tests, 95% coverage). Rerun the command if you want to quote a current number.

1. **Built decision-pack, a Python and FastAPI analysis engine with a Next.js front end, that turns a metric gap and a CSV into a driver bridge, segment scan, hypothesis tree, sized recommendations, memo and PPTX deck from one YAML spec; 264 tests, 95% branch coverage, mypy strict, ruff clean.**
   Proof: `pip install -e ".[dev]" && pytest --cov && mypy && ruff check src tests`

2. **Replaced an order-dependent cost bridge with exact Shapley attribution and showed the old "98.1% of the gap is post-click" headline ranges from 70.8% to 128.5% across substitution orders, against 96.8% when averaged; every number reproduced from the raw dataset in a regression test.**
   Proof: `pytest tests/test_bridge.py -k funnel_lab`

3. **Recomputed the headline numbers in a published funnel-analytics dashboard, corrected the claims that failed (visitor conversion, gender cost per conversion, click total, engagement-tier rates, interest counts), and added 20 tests that recompute each from the raw CSVs so they cannot drift (64 tests in total).**
   Proof: `<funnel-lab>/tests/test_headline_numbers.py`, run `python -m pytest -q`; the fix commits are on the `product-polish` branch.

4. **Audited AetherScan's README, architecture notes and paper against the code and removed or rewrote the claims the code did not support (PostgreSQL, process-pool offload, a persistent audit table, unreproducible latency and load figures); fixed a clean-install failure that stopped 27 backend tests from running (232 passing, 2 skipped).**
   Proof: `<AetherScan>/docs/DOC_AUDIT.md`; `PYTHONPATH=. pytest backend/tests -c backend/pytest.ini --ignore=backend/tests/probe_cdse.py --ignore=backend/tests/probe_ogd_earthdata.py`

5. **Added the first tests and CI to SyncState, a Yjs-based collaborative editor: 34 tests including property-based checks that 200 random concurrent edit histories converge regardless of delivery order, plus a negative control and a record of a real bug (provider-origin updates dropped by the batcher).**
   Proof: `<syncstate>/tests/crdt-convergence.test.ts`, run `npm test`

6. **Wrote retrospective PRDs, RICE and ICE-scored roadmaps, decision logs, metrics plans, changelogs and 3 to 5 ready-to-open issue drafts for each of five existing projects, with every score marked as judgement and every metric marked as a plan rather than a result.**
   Proof: `docs/product/` and `docs/issues/` in each repository; for example `<appwrite-migration-guard>/docs/product/ROADMAP.md`

7. **Designed an uncertainty guardrail: a recommendation cannot be sized without low, base and high values and a stated source for every assumption, so the tool fails a run instead of printing a confident number; covered by tests and visible in the committed case packs.**
   Proof: `pytest tests/test_sizing.py tests/test_committed_packs.py`

8. **Measured a full analysis of a 1,000,000-row table (four-factor bridge, 47-segment scan, 1,000 bootstrap resamples) at 8.3 to 8.9 seconds and about 822 MB peak on a laptop, with a reproducible script, by bootstrapping large groups in 2,000 random blocks.**
   Proof: `python scripts/perf_check.py --rows 1000000`

## What these bullets do not claim

No users, no adoption, no revenue, and no experiment run on a real product. Every project here is one I built or documented myself (AetherScan was built by a team of four, and I worked on the backend). The roadmaps and recommendations are proposals.
