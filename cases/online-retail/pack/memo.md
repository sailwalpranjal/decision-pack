# Average order value rose from one year to the next because orders grew longer and prices rose, while each line carried fewer units

*This is observational data. Differences between groups are described, not explained; nothing here shows that one factor caused another.*

## Summary

**Situation.** Average order value was £490.48 for Dec 2009 to Nov 2010 and £546.82 for Dec 2010 to Nov 2011.

**Complication.** The gap between them is £56.34 (1.11x), higher for Dec 2010 to Nov 2011, which is better. The 95% bootstrap interval for the gap is +£41.68 to +£71.38.

**Question.** Which part of average order value explains the gap, and what should we do?

**Answer.** Order length accounts for 114% of the gap. Substituting one factor at a time would put it anywhere from 103% to 126%; the Shapley split averages over every order. The first recommendation is to find out why units per line fell, starting with whether bulk buyers are ordering less or the customer mix changed (base impact 104,663 pounds of revenue protected over a comparable year; range 0 to 313,989).

## What drives the gap

Cost is split into factors that multiply to average order value. Each row shows how much of the £56.34 gap a factor carries.

| Factor | Dec 2009 to Nov 2010 | Dec 2010 to Nov 2011 | Shapley | Share | Sequential |
| --- | ---: | ---: | ---: | ---: | ---: |
| Order length (invoice lines per invoice) | 24.34 | 27.53 | +£64.09 | 113.8% | +£64.45 |
| Line size (units per invoice line) | 11.54 | 10.35 | -£56.71 | -100.7% | -£57.31 |
| Unit price (revenue per unit sold) | 1.746 | 1.919 | +£48.96 | 86.9% | +£49.20 |

Sequential substitution used the order Order length -> Line size -> Unit price. It depends on that order; the Shapley column averages over every order and does not.
For order length, the share ranges from 102.6% to 125.7% across the 6 possible orders.

## Where the gap concentrates

Rate scanned: bulk-line share. Overall 25.10% for Dec 2009 to Nov 2010 and 24.62% for Dec 2010 to Nov 2011. 21 segments were compared; p-values are adjusted (BH) and a segment needs at least 2000 in the denominator in each group.

| Segment | Dec 2009 to Nov 2010 | Dec 2010 to Nov 2011 | Contribution | Adj. p | Differs? |
| --- | ---: | ---: | ---: | ---: | --- |
| Country = United Kingdom | 22.96% | 22.22% | -0.88 pp | 1.01e-16 | yes |
| month_of_year = 12 | 20.67% | 19.43% | +0.49 pp | 2.15e-06 | yes |
| price_band = 1 to 3 | 26.81% | 27.31% | -0.41 pp | 0.00037 | yes |
| month_of_year = 4 | 26.66% | 25.67% | -0.39 pp | 0.00994 | yes |
| month_of_year = 10 | 27.78% | 26.01% | -0.35 pp | 4.67e-11 | yes |
| month_of_year = 3 | 24.27% | 25.32% | -0.28 pp | 0.0021 | yes |
| month_of_year = 9 | 30.69% | 30.02% | +0.23 pp | 0.0393 | yes |
| Country = France | 48.61% | 46.44% | +0.21 pp | 0.0215 | yes |

- Country: 3 of 5 segments carry 80% of the absolute gap (United Kingdom, France, EIRE).
- month_of_year: 6 of 12 segments carry 80% of the absolute gap (12, 4, 10, 3, 9, 6).
- price_band: 2 of 4 segments carry 80% of the absolute gap (1 to 3, under 1).
- No reversal across 'price_band' (4 levels compared).
- 38 segment(s) were set aside (too small, one group only, missing values or not a rate).

## What the hypothesis tree says

The data supports 3, refutes 1 and cannot settle 1.

- **UNTESTED** `gap`: Average order value is higher in the second year than in the first. (no test is attached to this node)
- **SUPPORTED** `length`: Orders got longer, with more lines on each invoice. (113.8% of the gap (threshold 50%; Shapley split))
- **REFUTED** `size`: Each line carries more units. (-100.7% of the gap (threshold 25%; Shapley split))
- **SUPPORTED** `bulk`: A smaller share of lines are bulk lines (12 or more units). (rate 25.10% -> 24.62% (diff -0.48%, p = 1.67e-08); the gap is in the claimed direction (lower))
- **SUPPORTED** `price`: Each unit sold brings in more revenue. (86.9% of the gap (threshold 25%; Shapley split))

## Recommendations

Impact is shown as low, base and high. Scores are the author's judgement.

| # | Recommendation | Base | Range | Score |
| ---: | --- | ---: | ---: | ---: |
| 1 | Find out why units per line fell, starting with whether bulk buyers are ordering less or the customer mix changed | 104,663 | 0 to 313,989 | 5.67 |
| 2 | Test an order-value threshold, such as free delivery just above today's average order, on a sample of customers | 156,994 | 0 to 418,652 | 5.33 |
| 3 | Record a customer id on every order, then repeat the analysis by customer | 52,331 | 0 to 209,326 | 4.33 |

**1. Find out why units per line fell, starting with whether bulk buyers are ordering less or the customer mix changed** (pounds of revenue protected over a comparable year). Units per line fell about 10% and the share of bulk lines (12 or more units) dipped slightly. A change in who buys and a change in how much each buyer takes need different responses.
- ICE = (5 + 5 + 7) / 3 = 5.67
- Most sensitive to `protected_share`: 0 to 313,989 across its range.
- `invoices`: 19141 / 19141 / 19141 (low / base / high). Source: Invoices in Dec 2010 to Nov 2011 in the dataset.
- `aov`: 546.8 / 546.8 / 546.8 (low / base / high). Source: Average order value in the same year, from the data.
- `protected_share`: 0 / 0.01 / 0.03 (low / base / high). Source: My judgement; share of revenue that acting on the finding would protect.

**2. Test an order-value threshold, such as free delivery just above today's average order, on a sample of customers** (pounds of extra revenue over a comparable year). Longer orders account for more than the whole rise in average order value (114% of it, partly cancelled by smaller lines), so nudging orders slightly longer is the lever the data points to. Whether a threshold would do it is a hypothesis, not something this data shows.
- ICE = (6 + 4 + 6) / 3 = 5.33
- Most sensitive to `uplift`: 0 to 418,652 across its range.
- `invoices`: 19141 / 19141 / 19141 (low / base / high). Source: Invoices in Dec 2010 to Nov 2011 in the dataset.
- `aov`: 546.8 / 546.8 / 546.8 (low / base / high). Source: Average order value in the same year, from the data.
- `uplift`: 0 / 0.015 / 0.04 (low / base / high). Source: My judgement, no test has been run; relative rise in average order value among invoices that see the threshold.

**3. Record a customer id on every order, then repeat the analysis by customer** (pounds of revenue influenced by decisions the data would then support). 23% of lines have no customer id, so repeat purchase and customer-level questions cannot be asked of this data at all.
- ICE = (4 + 4 + 5) / 3 = 4.33
- Most sensitive to `share_unlocked`: 0 to 209,326 across its range.
- `invoices`: 19141 / 19141 / 19141 (low / base / high). Source: Invoices in Dec 2010 to Nov 2011 in the dataset.
- `aov`: 546.8 / 546.8 / 546.8 (low / base / high). Source: Average order value in the same year, from the data.
- `share_unlocked`: 0 / 0.005 / 0.02 (low / base / high). Source: My judgement; share of revenue that customer-level decisions would improve.

## What this cannot tell you

- Observational data: groups were not randomly assigned, so gaps are not effects.
- Shapley attributions depend on how the metric is split into factors. A different factorisation gives different numbers.
- Segments that stand out are places to look, not causes. The scan corrects p-values for the number of segments compared, but cannot add information the data does not hold.
- Impact estimates rest on assumptions the author wrote down, each with a source; they are not forecasts.
- Intervals come from a bootstrap over rows and describe sampling noise only, not bias.
- Data: UCI Machine Learning Repository, Online Retail II (CC BY 4.0): invoice lines from a UK-based online retailer, December 2009 to December 2011. 1,067,371 lines in the file; 1,016,558 are sales lines in the two full years analysed.
- Data: A sales line has a positive quantity and price on a non-cancelled invoice. Cancellations, returns and zero-price lines are excluded, so revenue here is gross of returns.
- Data: Y1 is December 2009 to November 2010, Y2 is December 2010 to November 2011. December 2011 is dropped because the data end on 9 December.
- Data: 23% of lines in the file carry no customer id, so nothing here is about customers, only about invoices and lines.
- Data: The comparison is across calendar years of one business. Seasonality is the same in both years, but anything else that changed (assortment, pricing policy, customer mix) is mixed together.
- Note: Observational data: the groups were not randomly assigned, so gaps describe differences, not causes.
- Note: The segment scan compared 21 segments; p-values are adjusted for that (BH).
- Note: 38 segment(s) were set aside; see the scan table.
