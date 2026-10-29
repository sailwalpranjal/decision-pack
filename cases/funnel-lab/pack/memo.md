# Why campaign 1178 costs four times as much per approved conversion as campaign 936

*This is observational data. Differences between groups are described, not explained; nothing here shows that one factor caused another.*

## Summary

**Situation.** Cost per approved conversion was $15.81 for Campaign 936 and $63.83 for Campaign 1178.

**Complication.** The gap between them is $48.02 (4.04x), higher for Campaign 1178, which is worse. The 95% bootstrap interval for the gap is +$40.44 to +$55.34.

**Question.** Which part of cost per approved conversion explains the gap, and what should we do?

**Answer.** Click to enquiry accounts for 93% of the gap. Substituting one factor at a time would put it anywhere from 67% to 127%; the Shapley split averages over every order. The first recommendation is to test a shorter enquiry form on the campaign 1178 landing page (base impact 177 extra approved conversions over the same period; range 50 to 390).

## What drives the gap

Cost is split into factors that multiply to cost per approved conversion. Each row shows how much of the $48.02 gap a factor carries.

| Factor | Campaign 936 | Campaign 1178 | Shapley | Share | Sequential |
| --- | ---: | ---: | ---: | ---: | ---: |
| Media cost (spend per impression) | 0.000356 | 0.0002718 | -$11.00 | -22.9% | -$3.74 |
| Ad appeal (impressions needed per click) | 4097 | 5679 | +$12.52 | 26.1% | +$4.66 |
| Click to enquiry (clicks needed per enquiry) | 3.695 | 13.51 | +$44.84 | 93.4% | +$44.47 |
| Enquiry to approval (enquiries needed per approval) | 2.934 | 3.061 | +$1.66 | 3.5% | +$2.64 |

Sequential substitution used the order Media cost -> Ad appeal -> Click to enquiry -> Enquiry to approval. It depends on that order; the Shapley column averages over every order and does not.
For click to enquiry, the share ranges from 66.8% to 126.5% across the 24 possible orders.

## Where the gap concentrates

Rate scanned: click-to-approved rate. Overall 9.22% for Campaign 936 and 2.42% for Campaign 1178. 8 segments were compared; p-values are adjusted (BH) and a segment needs at least 200 in the denominator in each group.

| Segment | Campaign 936 | Campaign 1178 | Contribution | Adj. p | Differs? |
| --- | ---: | ---: | ---: | ---: | --- |
| gender = F | 5.88% | 1.76% | -3.75 pp | 2.04e-29 | yes |
| age = 30-34 | 30.77% | 4.32% | -3.34 pp | 3.62e-88 | yes |
| gender = M | 24.79% | 3.47% | -3.05 pp | 2.26e-89 | yes |
| age = 45-49 | 3.24% | 1.33% | -1.35 pp | 5.07e-07 | yes |
| interest = 16 | 4.02% | 2.35% | -1.33 pp | 0.00681 | yes |
| age = 35-39 | 12.36% | 2.46% | -1.25 pp | 6.19e-22 | yes |
| interest = 10 | 8.90% | 2.21% | -0.87 pp | 1.21e-09 | yes |
| age = 40-44 | 8.04% | 1.90% | -0.87 pp | 4.3e-13 | yes |

- age: 3 of 4 segments carry 80% of the absolute gap (30-34, 45-49, 35-39).
- gender: 2 of 2 segments carry 80% of the absolute gap (F, M).
- interest: 2 of 2 segments carry 80% of the absolute gap (16, 10).
- No reversal across 'age' (4 levels compared).
- No reversal across 'gender' (2 levels compared).
- 38 segment(s) were set aside (too small, one group only, missing values or not a rate).

## What the hypothesis tree says

The data supports 3, refutes 1 and cannot settle 2.

- **UNTESTED** `gap`: Cost per approved conversion is higher in campaign 1178 than in campaign 936. (no test is attached to this node)
- **REFUTED** `media`: Media got more expensive, so each impression costs more. (-23.1% of the gap (threshold 25%; Shapley split))
- **SUPPORTED** `appeal`: The ads attract fewer clicks per impression. (26.3% of the gap (threshold 25%; Shapley split))
- **SUPPORTED** `post_click`: Clicks turn into approved conversions at a much lower rate. (96.8% of the gap (threshold 25%; Shapley split))
- **SUPPORTED** `enquiry`: Fewer clicks turn into an enquiry. (rate 27.07% -> 7.40% (diff -19.67%, p = 5.06e-207); the gap is in the claimed direction (lower))
- **UNTESTED** `approval`: Fewer enquiries are approved. (not significant (p = 0.527) and underpowered: power to detect a 20% change is 68%, below 80%)

## Recommendations

Impact is shown as low, base and high. Scores are the author's judgement.

| # | Recommendation | Base | Range | Score |
| ---: | --- | ---: | ---: | ---: |
| 1 | Test a shorter enquiry form on the campaign 1178 landing page | 177 | 50 to 390 | 6.33 |
| 2 | Check the ad promise against the landing page before scaling spend further | 70 | 17 to 131 | 5.67 |
| 3 | Run a landing-page test for the female audience, which clicks more but converts less | 89 | 0 to 252 | 5.00 |

**1. Test a shorter enquiry form on the campaign 1178 landing page** (extra approved conversions over the same period). Most clicks never become an enquiry, and that stage carries the largest part of the cost gap.
- ICE = (8 + 5 + 6) / 3 = 6.33
- Most sensitive to `lift`: 59 to 354 across its range.
- `clicks`: 36068 / 36068 / 36068 (low / base / high). Source: Campaign 1178 clicks in the dataset.
- `lift`: 0.005 / 0.015 / 0.03 (low / base / high). Source: My judgement, no test has been run; absolute rise in the click-to-enquiry rate.
- `approval_rate`: 0.28 / 0.327 / 0.36 (low / base / high). Source: Approved per enquiry in campaign 1178 (about 32.7%); range is my judgement.

**2. Check the ad promise against the landing page before scaling spend further** (extra approved conversions over the same period). Campaign 1178 spent 19 times as much and the post-click funnel did not keep up.
- ICE = (7 + 4 + 6) / 3 = 5.67
- Most sensitive to `improvement`: 17 to 131 across its range.
- `spend`: 55662 / 55662 / 55662 (low / base / high). Source: Campaign 1178 spend in the dataset.
- `improvement`: 0.02 / 0.08 / 0.15 (low / base / high). Source: My judgement; share of cost per approved conversion removed.
- `cost_per_approved`: 63.83 / 63.83 / 63.83 (low / base / high). Source: Campaign 1178 in the dataset.

**3. Run a landing-page test for the female audience, which clicks more but converts less** (extra approved conversions over the same period). Across all three campaigns, female ad sets have a higher click rate than male ones (0.0208% against 0.0145%) but a higher cost per approved conversion ($69.70 against $41.44). That pattern is observational and the cause is unknown, which is why this is a test and not a rollout.
- ICE = (5 + 3 + 7) / 3 = 5.00
- Most sensitive to `lift`: 0 to 222 across its range.
- `clicks`: 36068 / 36068 / 36068 (low / base / high). Source: Campaign 1178 clicks in the dataset.
- `share`: 0.5 / 0.615 / 0.7 (low / base / high). Source: Female share of campaign 1178 clicks in the dataset (61.5%); range is my judgement.
- `lift`: 0 / 0.004 / 0.01 (low / base / high). Source: My judgement; absolute rise in click-to-approved rate for that audience.

## What this cannot tell you

- Observational data: groups were not randomly assigned, so gaps are not effects.
- Shapley attributions depend on how the metric is split into factors. A different factorisation gives different numbers.
- Segments that stand out are places to look, not causes. The scan corrects p-values for the number of segments compared, but cannot add information the data does not hold.
- Impact estimates rest on assumptions the author wrote down, each with a source; they are not forecasts.
- Intervals come from a bootstrap over rows and describe sampling noise only, not bias.
- Data: Public, anonymised ad-set data (Kaggle "Sales Conversion Optimization"), 1,143 ad sets across three campaigns. Each row is one ad set.
- Data: The campaigns did not run as a concurrent split test, so this is an observational comparison.
- Data: Revenue is not in the data, so CAC and ROAS are not computed.
- Note: Observational data: the groups were not randomly assigned, so gaps describe differences, not causes.
- Note: The segment scan compared 8 segments; p-values are adjusted for that (BH).
- Note: 38 segment(s) were set aside; see the scan table.
