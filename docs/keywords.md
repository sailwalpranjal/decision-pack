# Role keywords mapped to evidence

A keyword is listed against a role only where a file shows the thing. Paths are relative to the repository named; `dp` is this repository. If there is nothing, the line says so in the last section.

## Associate Product Manager

| Keyword | Evidence |
|---|---|
| PRD, problem statement, target user | `dp/docs/product/PRD.md`; `docs/product/PRD.md` in each of the five pinned repositories (marked "retrospective, written after the build" where that is true) |
| User stories and acceptance criteria | PRD tables in every repository; `docs/issues/*.md` drafts with acceptance checklists |
| Prioritisation, RICE, ICE | `dp/docs/product/ROADMAP.md` (arithmetic shown); `docs/product/ROADMAP.md` in each pinned repository; `dp/src/decisionpack/core/sizing.py` computes ICE and RICE with the arithmetic printed |
| Roadmap (Now / Next / Later) | `docs/product/ROADMAP.md` in each pinned repository |
| Metrics, KPIs, north star, guardrail metrics | PRD "success metrics" sections; `dp/docs/product/PRD.md` (north star: time from question to a defensible recommendation; guardrail: no result without stated uncertainty, enforced in `tests/test_sizing.py`) |
| User research | `dp/docs/research/interview-guide.md` (script for five interviews) and an empty `findings.md`, deliberately |
| Decision records | `dp/docs/DECISIONS.md`; `docs/product/DECISIONS.md` in each pinned repository |
| Stakeholder communication | `dp/src/decisionpack/report/memo.py` (SCQA memo, answer first) and `deck.py` (sentence titles); `dp/docs/launch.md` |

## Technical Product Manager

| Keyword | Evidence |
|---|---|
| REST API, OpenAPI | `dp/src/decisionpack/api/app.py` (typed models, async job endpoint, `/docs`); `funnel-lab/backend/main.py` |
| CI/CD | `.github/workflows/ci.yml` in every repository (Python matrix, Go, Maven, Node) |
| Data pipeline | `funnel-lab/sql/` and `scripts/` (raw CSV to cleaned tables to exports to dashboard JSON); `dp/cases/online-retail/prepare.py` |
| Technical trade-offs | `docs/product/DECISIONS.md` (for example SQLite first and PostgreSQL later in AetherScan; Yjs instead of a custom CRDT in SyncState; three-state verdict instead of a score in Appwrite Migration Guard) |
| Documenting limits and known gaps | `appwrite-migration-guard/docs/known-false-negatives.md`; `AetherScan/docs/DOC_AUDIT.md`; the "Limits" section of every README |
| Engineering credibility | `dp`: 264 tests, 95% coverage, mypy strict; `NitroDB`: 68 tests plus JCStress; `appwrite-migration-guard`: 225 top-level Go tests; `AetherScan`: 232 backend tests; `syncstate`: 34 tests |

## Technical Program Manager

| Keyword | Evidence |
|---|---|
| Release management, semantic versioning, changelog | `CHANGELOG.md` in each repository in Keep a Changelog style, with proposed `v0.x` tags (tagged locally in the pinned repositories) |
| Project board, labels, issue triage | `docs/project-board.md` and `scripts/create-labels.sh` in each repository |
| Agile, backlog | `docs/issues/` drafts from the "Now" items of each roadmap; issue and pull request templates in `.github/` |
| Risk management | "Risks and open questions" in each PRD |
| Quality gates | CI running tests, lint, type checks; recompute tests in the funnel lab (`tests/test_headline_numbers.py`) that fail the build if a published number drifts |

## Product Analyst

| Keyword | Evidence |
|---|---|
| Funnel analysis | `funnel-lab` (impression to click to enquiry to approval); `dp/cases/funnel-lab/` |
| Product analytics, KPIs | `dp/cases/online-shoppers/` (purchase rate by visitor type), `dp/cases/online-retail/` (average order value) |
| Experimentation, A/B testing, sample size, power | `dp/src/decisionpack/core/stats.py` (two-proportion z-test, power, sample size, SPRT, checked against SciPy and statsmodels); `funnel-lab/src/experiment_engine.py` (ICE-scored backlog, none run) |
| Statistical rigour, multiple comparisons | Holm and Benjamini-Hochberg in `stats.py`; segment scan in `core/segments.py`; Simpson's paradox check |
| Driver analysis, root-cause decomposition | `dp/src/decisionpack/core/bridge.py` (Shapley and sequential), with the funnel lab regression test |
| SQL, Python, pandas | `funnel-lab/sql/*.sql`, `src/*.py`; `dp` throughout |
| Data quality | `funnel-lab/src/validation.py` (11 checks); `AetherScan/backend/core/quality.py` (data quality and fusion confidence scores) |

## Product Operations

| Keyword | Evidence |
|---|---|
| Process and templates | Issue templates, PR templates, contributing, security and conduct files in every repository |
| Metrics instrumentation plans | `docs/product/METRICS.md` in each pinned repository (events and queries I would add; nothing measured) |
| Documentation hygiene | `AetherScan/docs/DOC_AUDIT.md`; the corrected claims in the funnel lab and the spectral path tracer README |
| Reporting | `dp/src/decisionpack/pack.py` writes memo, charts, CSVs and deck from one command |

## What I should not claim

- **Shipped to real users.** Nothing here has users that I can document.
- **Run experiments.** The experiment backlogs are proposals. No A/B test has been run.
- **Led a team or managed stakeholders.** AetherScan was built by a team of four, where I worked on the backend. The PM and program artefacts here are ones I wrote for my own projects.
- **Owned a roadmap against real constraints.** Scores are my judgement, not negotiated with anyone.
- **Revenue, adoption or retention results.** There are none.
