# The consulting-style method, and where it lives in the code

decision-pack borrows the *method* of strategy consulting: start from a question, split it into branches that do not overlap and do not leave anything out, test the branches, find the few that matter, and write the answer first. It does not borrow anything else, and it does not claim the results carry any firm's authority.

| Idea | What it means | Where it is in the code |
|---|---|---|
| Hypothesis-driven | Start from an answer you can be wrong about, then try to knock it down | `core/tree.py`: every node is a hypothesis that ends up supported, refuted or untested |
| Issue tree | Break the question into branches | `cases/*/tree.yaml`, loaded by `load_tree` |
| MECE | Branches that are mutually exclusive and collectively exhaustive | `validate_mece`: children must reproduce the parent's value in both groups, within 1e-6 |
| 80/20 | A few segments carry most of the effect | `core/segments.py`, `concentration()`: the fewest segments covering 80% of the absolute gap |
| Pyramid principle | Answer first, then the support, grouped | `report/memo.py` order; `report/deck.py` sentence titles |
| SCQA | Situation, complication, question, answer | `report/text.py`, `build_scqa` |

## Worked example: the funnel lab case

Spec: [`cases/funnel-lab/spec.yaml`](../cases/funnel-lab/spec.yaml). Output: [`cases/funnel-lab/pack/memo.md`](../cases/funnel-lab/pack/memo.md).

### 1. The question (the top of the tree)

Cost per approved conversion is $63.83 for campaign 1178 and $15.81 for campaign 936. The root of the tree says so:

```yaml
id: gap
statement: Cost per approved conversion is higher in campaign 1178 than in campaign 936.
metric: cost_per_approved
combine: product
```

### 2. Branches that add up (MECE)

Cost per approved conversion is spend per impression, times impressions per click, times clicks per approved conversion. Those are the three children. They are mutually exclusive in the sense that each measures a different step, and collectively exhaustive because their product *is* the parent. `validate_mece` checks that numerically in both campaigns. If I had written `clicks_per_enquiry` and forgotten `enquiries_per_approved` one level down, the product would not rebuild the parent and the run would say so, with both numbers.

The post-click branch is itself split into click-to-enquiry and enquiry-to-approval, again as a product.

### 3. Hypotheses, tested

Each branch is a statement the data can contradict:

- *Media got more expensive.* Share of the gap by Shapley split: -23.1%. Media actually got cheaper, so this is **refuted**.
- *The ads attract fewer clicks per impression.* 26.3% of the gap, over the 25% threshold I set: **supported**, narrowly.
- *Clicks turn into approved conversions at a much lower rate.* 96.8%: **supported**.
- *Fewer clicks turn into an enquiry.* 27.07% to 7.40%, p = 5e-207: **supported**.
- *Fewer enquiries are approved.* Not significant, and only 68% power to detect a 20% relative change: **untested**. The tool does not call it refuted, because it could not have told.

The thresholds (25%, 20%) are mine and are written in `tree.yaml`, where a reader can disagree with them.

### 4. Why Shapley and not the old split

The branch shares above use the Shapley split, not the sequential one. With the lab's three factors, sequential substitution gave conversion 98.1% of the gap. Averaged over all six orders it is 96.8%, and across the orders it ranges from 70.8% to 128.5%. A share that can land anywhere in a 58-point range depending on a choice nobody wrote down is not a finding; the average over orders is the defensible number. That is the main reason this project exists.

### 5. 80/20

The segment scan finds where the click-to-approved rate gap concentrates. `concentration()` returns the fewest segments of a dimension that carry 80% of the absolute gap, and the memo prints them: for age, 3 of 4 segments. The scan only reports segments with at least 200 clicks in both campaigns, corrects p-values for the 8 segments compared, and sets aside 38 as too small or present in one campaign only, saying so.

### 6. Pyramid and SCQA

The memo opens with the answer, as SCQA:

- **Situation.** Cost per approved conversion was $15.81 for campaign 936 and $63.83 for campaign 1178.
- **Complication.** The gap is $48.02 (4.04x), with a 95% bootstrap interval of +$40.44 to +$55.34.
- **Question.** Which part of cost per approved conversion explains the gap, and what should we do?
- **Answer.** Click-to-enquiry carries 93% of the gap; the first recommendation is to test a shorter enquiry form.

Below that, each section supports one claim from the answer. The deck follows the same order, and every slide title is a full sentence stating the conclusion of that slide, so reading only the titles gives the argument.

## What the method does not do

It does not make the conclusion causal, it does not choose the factorisation for you, and it does not replace asking people. The interview guide in [`docs/research/interview-guide.md`](research/interview-guide.md) is how the project plans to find out whether analysts want this at all.
