# Case study: funnel lab, campaign 936 against campaign 1178

**Status: observational.** The three campaigns in this dataset did not run as a concurrent split test. Everything below describes differences. None of it shows a cause.

## Question

Campaign 1178 spent $55,662, about 19 times the $2,893 of campaign 936, and its cost per approved conversion was $63.83 against $15.81. A 4.04x gap. Is it media cost, ad appeal, or what happens after the click, and what should the team look at first?

## Where this comes from

This is the analysis my funnel lab already did with a sequential cost bridge. The lab documented its own limitation: the split depends on the order in which the factors are substituted. `decision-pack` was built to remove that limitation, and this case is the regression check that it reproduces the lab's numbers before going further.

## What the pack found

All numbers are in [pack/memo.md](pack/memo.md) and [pack/result.json](pack/result.json).

- The gap is $48.02. A bootstrap over ad sets gives a 95% interval of +$40.44 to +$55.34.
- **The old split reproduces.** In the lab's three-factor form (CPM, CTR, click-to-approved) sequential substitution gives CPM -$3.74, CTR +$4.66, conversion +$47.10, which is 98.1% of the gap after the click.
- **The order matters.** Across all six orders of those three factors the conversion share runs from 70.8% to 128.5%. The Shapley split, which averages over the orders, is CPM -$11.08, CTR +$12.62, conversion +$46.48: **96.8%**. `tests/test_bridge.py` pins every one of these numbers.
- **The conclusion survives, the precision does not.** Conversion after the click carries most of the gap under every ordering and under Shapley, but "98.1%" was one of six possible answers.
- **Splitting the post-click step further** (this pack uses four factors): click-to-enquiry carries 93.4% of the gap (+$44.84 of $48.02), enquiry-to-approval only 3.5%, ad appeal 26.1%, media cost -22.9% (media got cheaper, which works against the gap). In campaign 1178, 7.4% of clicks became an enquiry; in campaign 936, 27.1%.
- **Hypothesis tree** (`tree.yaml`): media cost refuted, ad appeal supported at a low threshold, post-click supported, click-to-enquiry supported, enquiry-to-approval untested (not significant, and underpowered for a 20% relative change).
- **Segment scan** of click-to-approved rate by age, gender and interest: 8 segments passed the minimum-size rule (at least 200 clicks in both campaigns) and all 8 differ after correction; 38 were set aside as too small or present in one campaign only. No Simpson's-paradox reversal across age or gender.

## What to do (proposed, none tried)

The pack ranks three recommendations by ICE. They are proposals, each with low, base and high assumptions and a source written next to every number:

1. Test a shorter enquiry form on the campaign 1178 landing page.
2. Check the ad promise against the landing page before scaling spend further.
3. Run a landing-page test for the female audience.

Scores and ranges are my judgement. No test has been run.

## What this cannot tell you

- That anything *caused* the gap. Campaign 1178 may be a later, broader phase of the same effort, with a different audience.
- That the four-factor split is the only sensible one. Shapley depends on the factorisation.
- Anything about revenue. The data has none, so CAC and ROAS are not computed.

## Data and licence

- File: `data/KAG_conversion_data.csv`, 1,143 ad sets across three campaigns (936, 916 and 1178). Source: Kaggle, "Sales Conversion Optimization". It is not committed; `prepare.py` fetches it and checks the SHA-256.
- Licence: Kaggle lists it as "Other (specified in description)", and the description gives no terms. I therefore do not redistribute the file; the committed pack contains only aggregates computed from it.
- Quirks found while running: 72 ad sets report approved conversions with zero clicks, and 218 report more enquiries than clicks (conversions credited without a click, probably). They stay in the data; they are why the segment scan sets aside segments whose "rate" exceeds 1.

## Reproduce

```bash
python cases/funnel-lab/prepare.py
decisionpack run cases/funnel-lab/spec.yaml cases/funnel-lab/data/KAG_conversion_data.csv --out cases/funnel-lab/pack
```
