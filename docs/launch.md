# Launch drafts

Drafts only. Nothing here has been posted. Every number comes from the repository and can be reproduced with the command next to it. Replace `<repo-url>` before posting. I have no users yet, so none of these drafts claims any.

Numbers used, and where they come from:

| Number | Source |
|---|---|
| $15.81 against $63.83, a $48.02 gap (4.04x) | `pytest tests/test_bridge.py::test_funnel_lab_regression` |
| sequential split 98.1% post-click; 70.8% to 128.5% across the six orders; Shapley 96.8% | `tests/test_bridge.py::test_funnel_lab_regression` and `::test_funnel_lab_order_sensitivity` |
| 264 tests, 95% line and branch coverage | `pytest --cov` on the commit these drafts were written against |
| 8.3 to 8.9 seconds for 1,000,000 rows, about 822 MB peak | `python scripts/perf_check.py` on one Windows machine, three runs |
| three cases: funnel lab, online shoppers (CC BY 4.0), online retail (CC BY 4.0) | `cases/` |

---

## Dev.to post

**Title:** The share of the gap I reported depended on the order I did the sums in

**Tags:** python, datascience, productmanagement, statistics

I had a clean headline from a public ad dataset. Two campaigns, cost per approved conversion $15.81 against $63.83, a $48.02 gap. I split the gap into three factors (media cost, click rate, post-click conversion) by changing one factor at a time from campaign A's value to campaign B's, and the answer was tidy: 98.1% of the gap sits after the click.

The project's own notes list, as a limitation, that this split depends on the order. Here is how much: the same data gives anything from 70.8% to 128.5% for the post-click share, depending on which factor is swapped first. A share that moves by 58 points because of a choice nobody wrote down is not a finding.

The fix is a standard one from cooperative game theory: the Shapley value. Average each factor's marginal effect over every order in which the factors could be swapped. It does not depend on the order, and the parts still add up exactly to the gap. For the same data it gives 96.8% post-click. The conclusion survives. The precision I claimed did not.

That became a small project, decision-pack, which does the rest of what I would want before telling a team what to do about a gap:

- a driver bridge with Shapley and sequential attribution, side by side
- a segment scan that corrects for how many segments it looked at, refuses segments with too little data, and flags Simpson's-paradox reversals
- an issue tree in YAML where the branches must multiply or add back to the parent, checked numerically, with each hypothesis marked supported, refuted or untested
- sized recommendations where every assumption has a low, base and high value and a source, or the run refuses to finish
- a one-page memo and a deck whose slide titles are full sentences

Some things I did to keep it honest. Every statistics function is tested against SciPy or statsmodels. The Shapley code is tested with property-based tests: the parts sum to the gap, and shuffling the factor order changes nothing. There are 264 tests at 95% coverage, and a full run on a million rows takes about 8 seconds on my laptop.

What it cannot do: it does not show causes, the Shapley split still depends on how you factor the metric, and nobody except me has used it. I have written an interview plan for five people who explain metric gaps for a living and left the findings file empty until I have done them.

Code, three worked cases on public data, and the committed output: `<repo-url>`

---

## Show HN

**Title:** Show HN: Explain a metric gap without choosing an order (Shapley driver analysis)

**Text:**

I split a cost gap between two ad campaigns into factors by swapping one factor at a time, and reported that 98.1% of the gap was after the click. Trying all six orders gives anywhere from 70.8% to 128.5% on the same data. This project replaces that split with Shapley attribution, which averages over orders, is exact, and gives 96.8% here.

Around that it has a segment scan with multiple-comparison correction and Simpson's-paradox flags, YAML issue trees whose branches have to add up numerically, sized recommendations that require a low/base/high range and a source for every assumption, and a memo plus PPTX deck. Python, FastAPI, a small Next.js page. 264 tests, statistics checked against SciPy and statsmodels, 1M rows in about 8 seconds on my machine.

Limits, up front: observational data only, so it describes gaps and does not explain them; Shapley depends on how you factor the metric; and I have no users yet. The repo includes three worked cases on public datasets and the interview guide I will use to find out whether anyone wants this.

`<repo-url>`

---

## LinkedIn

I reported that 98.1% of a cost gap was "after the click". Changing the order of the arithmetic gives anywhere from 70.8% to 128.5%.

That bothered me enough to build decision-pack: an analysis tool that splits a metric gap between drivers in a way that does not depend on order (Shapley values), scans segments with proper multiple-comparison control, checks that an issue tree actually adds up, and will not size a recommendation without a low, base and high case.

It is tested (264 tests, statistics checked against SciPy and statsmodels), it has three worked cases on public data, and it says plainly what it cannot tell you: it describes observational data, it does not prove causes.

No users yet. I have written an interview plan for five PMs and analysts and I would like to talk to some of you. If you have explained a metric gap to a stakeholder in the last few months, I would value 20 minutes.

`<repo-url>`
