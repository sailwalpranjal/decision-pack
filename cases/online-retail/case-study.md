# Case study: online retail, why average order value rose

**Status: observational.** Two calendar years of one business. Seasonality is the same in both, but anything else that changed (assortment, pricing, customer mix) is mixed together. Nothing here shows a cause.

## Question

Average order value (revenue per invoice) was £490.48 in December 2009 to November 2010 and £546.82 in December 2010 to November 2011, up £56.34. What moved?

## What the pack found

Numbers are from [pack/memo.md](pack/memo.md) and [pack/result.json](pack/result.json).

- The gap is +£56.34 (1.11x). A bootstrap interval (500 resamples, large groups bootstrapped in blocks) gives +£41.68 to +£71.38.
- Average order value is lines per invoice, times units per line, times revenue per unit. The three factors multiply back to the metric exactly, and the tree checks that.
- **Shapley split:** order length +£64.09 (114% of the gap), line size -£56.71 (-101%), unit price +£48.96 (87%). The shares add to 100%; two of the factors move the metric more than it moved in total because the third works against them.
- Substituting one factor at a time would put order length anywhere between 103% and 126%, so the sign and rough size survive any ordering, but the exact share does not.
- **In words:** invoices got longer (24.3 to 27.5 lines on average) and each unit brought in more (£1.75 to £1.92), while each line carried fewer units (11.5 to 10.4).
- **Tree:** order length supported, unit price supported, line size refuted as an *increase* (it fell), and "a smaller share of lines are bulk lines" supported (25.10% to 24.62%, a half-point change that is statistically clear because of the sample size and small in size).
- **Segment scan** of the bulk-line share across country, month of year and price band: 21 segments cleared the minimum size of 2,000 lines in both years; 38 were set aside. No Simpson's-paradox reversal across price band. The scan shows the small change spread across segments, with the United Kingdom, December and the 1-to-3 price band carrying the most.

## What to do (proposed, none tried)

Three recommendations, ICE-scored, each with low, base and high assumptions and a source:

1. Find out why units per line fell, starting with whether bulk buyers are ordering less or the customer mix changed.
2. Test an order-value threshold, such as free delivery just above today's average order.
3. Record a customer id on every order, then repeat the analysis by customer.

The ranges start at zero because I have no evidence about the effect size of any of them. The scores and ranges are my judgement.

## What this cannot tell you

- Anything about customers: 23% of lines in the file have no customer id.
- Whether prices rose or the mix shifted towards dearer items. Revenue per unit mixes both.
- Revenue net of returns. Cancellations and zero-price lines are excluded, so the revenue is gross.

## Data and licence

CC BY 4.0, as stated on the UCI dataset page; see `README.md` here for attribution and the checksum of the file I used. The raw file is not committed; `prepare.py` fetches it.
