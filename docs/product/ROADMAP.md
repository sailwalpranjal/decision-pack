# Roadmap

RICE = Reach x Impact x Confidence / Effort. Reach: how many of the target users hit the item, 1-10. Impact: 0.25 minimal, 0.5 low, 1 medium, 2 high, 3 massive. Confidence: my confidence in the first two, as a fraction. Effort: person-weeks. All scores are my judgement, not data.

Releases follow the order in which the repository is built.

## v0.1: core and CLI

| Item | R | I | C | E | RICE | Why first |
|---|---|---|---|---|---|---|
| Driver bridge: sequential and Shapley | 9 | 3 | 0.9 | 1.0 | 9 x 3 x 0.9 / 1.0 = **24.3** | The reason the project exists; fixes a flaw I documented in the funnel lab |
| Statistics: z-test, Wilson, bootstrap, power, Holm, BH | 9 | 2 | 0.9 | 1.5 | 9 x 2 x 0.9 / 1.5 = **10.8** | Every other module relies on honest uncertainty |
| Segment scan with Simpson's check | 8 | 2 | 0.7 | 1.5 | 8 x 2 x 0.7 / 1.5 = **7.5** | Where analysts lose most time |
| Hypothesis tree in YAML with MECE check | 7 | 2 | 0.7 | 1.5 | 7 x 2 x 0.7 / 1.5 = **6.5** | Gives structure; catches trees that do not add up |
| Impact sizing with low/base/high | 8 | 2 | 0.7 | 1.0 | 8 x 2 x 0.7 / 1.0 = **11.2** | Turns analysis into something a PM can act on |
| CLI `decisionpack run` | 8 | 1 | 0.9 | 0.5 | 8 x 1 x 0.9 / 0.5 = **14.4** | Cheap, makes everything usable |

## v0.2: report and deck

| Item | R | I | C | E | RICE | Why |
|---|---|---|---|---|---|---|
| SCQA summary and one-page memo | 9 | 2 | 0.8 | 1.0 | 9 x 2 x 0.8 / 1.0 = **14.4** | The artefact people actually read |
| SVG waterfall and tree charts | 7 | 1 | 0.8 | 1.0 | 7 x 1 x 0.8 / 1.0 = **5.6** | A bridge is much easier to read as a waterfall |
| PPTX deck, sentence titles, methods appendix | 6 | 1 | 0.6 | 1.5 | 6 x 1 x 0.6 / 1.5 = **2.4** | Lowest-confidence item: I do not yet know whether users want a deck. Interviews decide whether it stays |

## v0.3: API and web

| Item | R | I | C | E | RICE | Why |
|---|---|---|---|---|---|---|
| FastAPI with async job endpoint and typed models | 5 | 1 | 0.8 | 1.0 | 5 x 1 x 0.8 / 1.0 = **4.0** | Lets other tools call it |
| Minimal Next.js page: upload, waterfall, tree, recommendations | 6 | 1 | 0.6 | 1.5 | 6 x 1 x 0.6 / 1.5 = **2.4** | Lets someone try it without a terminal |

## v0.4: cases and polish

| Item | R | I | C | E | RICE | Why |
|---|---|---|---|---|---|---|
| Three public-data case studies with committed packs | 8 | 2 | 0.9 | 1.5 | 8 x 2 x 0.9 / 1.5 = **9.6** | Proof the method runs on real data, and the best demo |
| 1M-row performance check recorded in the README | 4 | 0.5 | 0.9 | 0.5 | 4 x 0.5 x 0.9 / 0.5 = **3.6** | Sets honest expectations |
| Docker image, pre-commit, CI matrix | 4 | 0.5 | 0.9 | 0.5 | 4 x 0.5 x 0.9 / 0.5 = **3.6** | Hygiene |

## After v0.4 (proposed, not scheduled)

- Run the five interviews and rework the roadmap from what they say.
- Additive decomposition for metrics that are sums rather than products.
- Bayesian intervals as an alternative to the bootstrap.
