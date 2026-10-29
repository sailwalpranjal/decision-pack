# Case study: online shoppers, new against returning visitors

**Status: observational.** New and returning visitors differ in many ways besides how they behave on the site. Everything below describes differences, not causes.

## Question

New visitors buy at a higher rate than returning visitors. Where in the session does the difference appear?

## What the pack found

Numbers are from [pack/memo.md](pack/memo.md) and [pack/result.json](pack/result.json).

- Purchase rate: 13.9% for returning visitors (10,551 sessions) and 24.9% for new visitors (1,694 sessions). The gap is 11.0 percentage points, with a 95% bootstrap interval of +8.9 to +13.1 points. 29 rows without a purchase label were dropped.
- **Both groups reach a "valued page" at the same rate**: 22.1% and 22.5% (p = 0.727; the test had 85% power to detect a 20% relative difference, so the tree marks "new visitors reach a valued page more often" as refuted, not untested).
- **After a valued page, the groups part ways**: 51.2% of returning visitors buy, against 86.4% of new visitors.
- The bridge splits the 11.0-point gap into three factors with an explicit formula (purchase rate = P(valued) x P(buy given valued) + P(not valued) x P(buy given not valued)). Shapley attribution: buying after a valued page 71.4%, buying without one 26.4%, reaching a valued page 2.2%. Across the six substitution orders the first share only moves between 70.8% and 72.0%, so on this case the order barely matters.
- The hypothesis tree adds up exactly (the two routes to a purchase sum to the purchase rate) and marks "the gap is in sessions that reach a valued page and then buy" as supported (73.7% of the gap).
- Segment scan across month, traffic type, operating system, browser, region and weekend: 33 segments compared with Benjamini-Hochberg adjustment. The gap shows up broadly, in most segments, rather than in one corner. No Simpson's-paradox reversal across month or weekend.

## A caution about the key variable

`PageValues` is computed from transaction outcomes, so a session that ends in a purchase is far more likely to have a positive value (81% of purchasing sessions do). The split between "reaching a valued page" and "buying after one" partly reflects how the variable is built. Read it as a description of the data, not as a funnel that a visitor walks through. The case is useful as a demonstration of the method, including the formula-based bridge, more than as a product finding.

## What to do (proposed, none tried)

Three recommendations, scored by ICE, each with low, base and high assumptions and a source:

1. Find out why returning visitors who reach a valued page convert far less often.
2. Test a resume-checkout prompt for returning visitors.
3. Repeat the comparison by traffic source, then act on the sources that differ.

Ranges and scores are my judgement. No test has been run.

## Data and licence

CC BY 4.0, as stated on the UCI dataset page. The CSV contains 125 exactly duplicated rows; they are left in. See `README.md` in this folder for attribution.

## Reproduce

```bash
decisionpack run cases/online-shoppers/spec.yaml cases/online-shoppers/data/online_shoppers_intention.csv --out cases/online-shoppers/pack
```
