# Add a second order-free method (LMDI) and compare it with Shapley

**Labels:** type:feature, priority:P1, area:bridge

## Problem

Shapley is not the only way to split a product's change without an order. Log-mean (LMDI) decomposition is exact for products and cheap, but is defined only for positive factors. Showing both on the case studies would say how much the choice of method matters, on top of the choice of factorisation.

## Acceptance criteria

- [ ] `core/bridge.py` has `lmdi_bridge(baseline, comparison)` for product metrics, rejecting non-positive factors with a clear message.
- [ ] Property tests: the attributions sum to the gap, and are invariant to the order of the factors.
- [ ] A test shows LMDI and Shapley agree closely on the funnel lab factors, or states by how much they differ.
- [ ] The memo adds one column or sentence only when the two methods disagree by more than 5 percentage points of share.
