# New visitors buy far more often than returning visitors, and the difference is in what happens after a valued page

*This is observational data. Differences between groups are described, not explained; nothing here shows that one factor caused another.*

## Summary

**Situation.** Purchase rate was 13.9% for Returning visitors and 24.9% for New visitors.

**Complication.** The gap between them is 11.0 pp (1.79x), higher for New visitors, which is better. The 95% bootstrap interval for the gap is +8.9 pp to +13.1 pp.

**Question.** Which part of purchase rate explains the gap, and what should we do?

**Answer.** Buying after a valued page accounts for 71% of the gap. Substituting one factor at a time would put it anywhere from 71% to 72%; the Shapley split averages over every order. The first recommendation is to find out why returning visitors who reach a valued page convert far less often than new visitors (base impact 140 extra purchases over the same period; range 47 to 280).

## What drives the gap

Cost is split into factors that multiply to purchase rate. Each row shows how much of the 11.0 pp gap a factor carries.

| Factor | Returning visitors | New visitors | Shapley | Share | Sequential |
| --- | ---: | ---: | ---: | ---: | ---: |
| Reaching a valued page (share of sessions that visit a page with a positive page value) | 0.2211 | 0.2249 | +0.2 pp | 2.2% | +0.2 pp |
| Buying after a valued page (purchase rate among sessions that reached one) | 0.5122 | 0.8635 | +7.8 pp | 71.4% | +7.9 pp |
| Buying without one (purchase rate among sessions that did not) | 0.03346 | 0.07083 | +2.9 pp | 26.4% | +2.9 pp |

Sequential substitution used the order Reaching a valued page -> Buying after a valued page -> Buying without one. It depends on that order; the Shapley column averages over every order and does not.
For buying after a valued page, the share ranges from 70.8% to 72.0% across the 6 possible orders.

## Where the gap concentrates

Rate scanned: purchase rate. Overall 13.93% for Returning visitors and 24.91% for New visitors. 33 segments were compared; p-values are adjusted (BH) and a segment needs at least 50 in the denominator in each group.

| Segment | Returning visitors | New visitors | Contribution | Adj. p | Differs? |
| --- | ---: | ---: | ---: | ---: | --- |
| Weekend = False | 13.18% | 26.09% | +8.51 pp | 1.25e-30 | yes |
| TrafficType = 2 | 20.50% | 25.43% | +8.29 pp | 0.00261 | yes |
| OperatingSystems = 2 | 15.88% | 27.35% | +6.61 pp | 1.32e-16 | yes |
| Browser = 2 | 14.31% | 22.64% | +4.51 pp | 2.83e-11 | yes |
| Region = 1 | 14.73% | 25.11% | +4.00 pp | 8.7e-11 | yes |
| OperatingSystems = 1 | 12.60% | 25.73% | +3.67 pp | 2.95e-11 | yes |
| Browser = 1 | 12.72% | 26.51% | +3.46 pp | 2.83e-11 | yes |
| Month = Dec | 9.62% | 22.39% | +3.21 pp | 6.43e-10 | yes |

- Month: 5 of 8 segments carry 80% of the absolute gap (Dec, May, Nov, Sep, Oct).
- TrafficType: 3 of 6 segments carry 80% of the absolute gap (2, 8, 5).
- OperatingSystems: 2 of 4 segments carry 80% of the absolute gap (2, 1).
- Browser: 3 of 4 segments carry 80% of the absolute gap (2, 1, 4).
- Region: 6 of 9 segments carry 80% of the absolute gap (1, 9, 6, 2, 5, 3).
- Weekend: 2 of 2 segments carry 80% of the absolute gap (False, True).
- No reversal across 'Month' (8 levels compared).
- No reversal across 'Weekend' (2 levels compared).
- 29 segment(s) were set aside (too small, one group only, missing values or not a rate).

## What the hypothesis tree says

The data supports 2, refutes 2 and cannot settle 1.

- **UNTESTED** `gap`: New visitors have a higher purchase rate than returning visitors. (no test is attached to this node)
- **SUPPORTED** `via_valued`: The gap comes from sessions that reach a valued page and then buy. (73.7% of the gap (threshold 50%; Shapley split))
- **REFUTED** `reach`: New visitors reach a valued page more often. (no difference as large as 20% (rate 22.11% -> 22.49%, p = 0.727); power to detect it was 85%)
- **SUPPORTED** `convert`: New visitors who reach a valued page are more likely to buy. (rate 51.22% -> 86.35% (diff +35.13%, p = 1.39e-37); the gap is in the claimed direction (higher))
- **REFUTED** `via_other`: The gap comes from purchases made without reaching a valued page. (26.3% of the gap (threshold 50%; Shapley split))

## Recommendations

Impact is shown as low, base and high. Scores are the author's judgement.

| # | Recommendation | Base | Range | Score |
| ---: | --- | ---: | ---: | ---: |
| 1 | Find out why returning visitors who reach a valued page convert far less often than new visitors | 140 | 47 to 280 | 5.67 |
| 2 | Test a resume-checkout prompt for returning visitors on valued pages | 70 | 0 to 187 | 5.33 |
| 3 | Repeat this comparison by traffic source, then act on the sources that differ | 63 | 0 to 264 | 5.33 |

**1. Find out why returning visitors who reach a valued page convert far less often than new visitors** (extra purchases over the same period). Both groups reach a valued page at about the same rate (22%), but 86% of new visitors buy after one and 51% of returning visitors do. That is where the gap sits.
- ICE = (8 + 4 + 5) / 3 = 5.67
- Most sensitive to `lift`: 47 to 280 across its range.
- `sessions`: 10551 / 10551 / 10551 (low / base / high). Source: Returning-visitor sessions with a purchase label in the dataset.
- `pv_rate`: 0.221 / 0.221 / 0.221 (low / base / high). Source: Share of returning sessions that reached a valued page, from the data.
- `lift`: 0.02 / 0.06 / 0.12 (low / base / high). Source: My judgement, no test has been run; absolute rise in purchase rate among returning sessions that reach a valued page.

**2. Test a resume-checkout prompt for returning visitors on valued pages** (extra purchases over the same period). A concrete intervention for recommendation 1. Whether the shortfall is a checkout problem is a hypothesis, not something this data shows.
- ICE = (6 + 3 + 7) / 3 = 5.33
- Most sensitive to `lift`: 0 to 187 across its range.
- `sessions`: 10551 / 10551 / 10551 (low / base / high). Source: Returning-visitor sessions in the dataset.
- `pv_rate`: 0.221 / 0.221 / 0.221 (low / base / high). Source: Share of returning sessions that reached a valued page, from the data.
- `lift`: 0 / 0.03 / 0.08 (low / base / high). Source: My judgement; absolute rise in purchase rate among those sessions.

**3. Repeat this comparison by traffic source, then act on the sources that differ** (extra purchases over the same period, if the follow-up finds something to act on). Traffic type is the dimension most likely to confound new versus returning, and the scan shows how much each source differs.
- ICE = (4 + 4 + 8) / 3 = 5.33
- Most sensitive to `lift`: 0 to 158 across its range.
- `sessions`: 10551 / 10551 / 10551 (low / base / high). Source: Returning-visitor sessions in the dataset.
- `share`: 0.1 / 0.3 / 0.5 (low / base / high). Source: My judgement; share of returning sessions that come from the sources that turn out to matter.
- `lift`: 0 / 0.02 / 0.05 (low / base / high). Source: My judgement; purchase-rate rise from acting on what the analysis finds.

## What this cannot tell you

- Observational data: groups were not randomly assigned, so gaps are not effects.
- Shapley attributions depend on how the metric is split into factors. A different factorisation gives different numbers.
- Segments that stand out are places to look, not causes. The scan corrects p-values for the number of segments compared, but cannot add information the data does not hold.
- Impact estimates rest on assumptions the author wrote down, each with a source; they are not forecasts.
- Intervals come from a bootstrap over rows and describe sampling noise only, not bias.
- Data: UCI Machine Learning Repository, Online Shoppers Purchasing Intention Dataset (CC BY 4.0). One row is one browsing session; 12,330 sessions have a purchase label.
- Data: PageValues is the average value of the pages a session visited before a transaction. A positive value means the session reached a page that has led to purchases; it is not revenue. It is computed from transaction outcomes, so a session that ends in a purchase is much more likely to have a positive value (81% of purchasing sessions do). The split between 'reaching a valued page' and 'buying after one' therefore partly reflects how the variable is built, and should be read as a description, not a funnel.
- Data: Returning and new visitors differ in many ways besides how they behave on the site. This is an observational comparison.
- Note: Observational data: the groups were not randomly assigned, so gaps describe differences, not causes.
- Note: The segment scan compared 33 segments; p-values are adjusted for that (BH).
- Note: 29 segment(s) were set aside; see the scan table.
