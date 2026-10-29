"""Hypothesis trees written in YAML.

An issue tree breaks a question into branches. Two rules make it more than a diagram:

* **MECE, checked numerically.** If a node says it is made of its children (``combine:
  product``, ``sum`` or ``ratio``), the children's values must reproduce the node's own value in
  both groups. A tree that does not add up is reported with the numbers.
* **Each node is marked supported, refuted or untested** from the analysis, using a stated test.
  A node with no test, or with data that cannot settle the question, is *untested*. The tool
  does not guess.

Values come from the caller as ``{metric_name: number}`` for the baseline and the comparison.
"""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from decisionpack.core.bridge import shapley_bridge
from decisionpack.core.stats import power_two_proportions, two_proportion_ztest

Combine = Literal["product", "sum", "ratio"]
Status = Literal["supported", "refuted", "untested"]

COMBINES = ("product", "sum", "ratio")
TEST_KINDS = ("share_of_gap", "rate_gap")
REL_TOL = 1e-6


class TreeError(ValueError):
    """The tree file is malformed."""


@dataclass(frozen=True)
class TreeNode:
    id: str
    statement: str
    metric: str | None = None
    combine: Combine | None = None
    test: Mapping[str, Any] | None = None
    children: tuple[TreeNode, ...] = ()

    def walk(self) -> Iterator[TreeNode]:
        yield self
        for child in self.children:
            yield from child.walk()


@dataclass(frozen=True)
class MeceProblem:
    node_id: str
    message: str


@dataclass(frozen=True)
class NodeResult:
    node_id: str
    statement: str
    status: Status
    detail: str
    statistic: float | None = None


@dataclass
class _Seen:
    ids: set[str] = field(default_factory=set)


def parse_tree(data: Mapping[str, Any]) -> TreeNode:
    return _parse(data, _Seen())


def _parse(data: Any, seen: _Seen) -> TreeNode:
    if not isinstance(data, Mapping):
        raise TreeError(f"a tree node must be a mapping; got {type(data).__name__}")
    node_id = data.get("id")
    if not node_id or not isinstance(node_id, str):
        raise TreeError(f"every node needs a string id; got {node_id!r}")
    if node_id in seen.ids:
        raise TreeError(f"duplicate node id {node_id!r}")
    seen.ids.add(node_id)
    statement = data.get("statement")
    if not statement or not isinstance(statement, str):
        raise TreeError(f"node {node_id!r} needs a statement")

    combine = data.get("combine")
    if combine is not None and combine not in COMBINES:
        raise TreeError(f"node {node_id!r}: combine must be one of {COMBINES}; got {combine!r}")
    raw_children = data.get("children") or []
    if not isinstance(raw_children, list):
        raise TreeError(f"node {node_id!r}: children must be a list")
    children = tuple(_parse(c, seen) for c in raw_children)
    if combine is not None:
        if not data.get("metric"):
            raise TreeError(f"node {node_id!r}: combine needs the node's own metric")
        if not children:
            raise TreeError(f"node {node_id!r}: combine needs children to combine")
        if combine == "ratio" and len(children) != 2:
            raise TreeError(f"node {node_id!r}: ratio needs exactly two children")
        for child in children:
            if not child.metric:
                raise TreeError(f"node {child.id!r}: needs a metric because its parent combines")

    test = data.get("test")
    if test is not None:
        if not isinstance(test, Mapping) or test.get("kind") not in TEST_KINDS:
            raise TreeError(f"node {node_id!r}: test kind must be one of {TEST_KINDS}")
    return TreeNode(
        id=node_id,
        statement=statement,
        metric=data.get("metric"),
        combine=combine,
        test=dict(test) if test else None,
        children=children,
    )


def load_tree(path: str | Path) -> TreeNode:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TreeError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, Mapping):
        raise TreeError(f"{path}: the top level must be a mapping describing the root node")
    return parse_tree(data)


# ---- MECE check ---------------------------------------------------------------------------


def _combine(kind: str, values: list[float]) -> float:
    if kind == "product":
        return math.prod(values)
    if kind == "sum":
        return sum(values)
    return values[0] / values[1] if values[1] != 0 else math.inf


def validate_mece(
    root: TreeNode, values_a: Mapping[str, float], values_b: Mapping[str, float]
) -> list[MeceProblem]:
    """Check that each combining node's children reproduce it in both groups."""
    problems: list[MeceProblem] = []
    for node in root.walk():
        if node.combine is None or node.metric is None:
            continue
        for label, values in (("baseline", values_a), ("comparison", values_b)):
            needed = [node.metric, *(c.metric or "" for c in node.children)]
            missing = [m for m in needed if m not in values]
            if missing:
                problems.append(
                    MeceProblem(node.id, f"{label}: no value for {', '.join(missing)}")
                )
                continue
            parts = [values[c.metric or ""] for c in node.children]
            rebuilt = _combine(node.combine, parts)
            own = values[node.metric]
            if not math.isclose(rebuilt, own, rel_tol=REL_TOL, abs_tol=1e-9):
                problems.append(
                    MeceProblem(
                        node.id,
                        f"{label}: {node.metric} is {own:g} but its children {node.combine} to "
                        f"{rebuilt:g}; the branches are not mutually exclusive and "
                        "collectively exhaustive",
                    )
                )
    return problems


# ---- evaluation ---------------------------------------------------------------------------


def _parent_of(root: TreeNode, target: TreeNode) -> TreeNode | None:
    for node in root.walk():
        if target in node.children:
            return node
    return None


def evaluate_tree(
    root: TreeNode, values_a: Mapping[str, float], values_b: Mapping[str, float]
) -> list[NodeResult]:
    """Mark every node supported, refuted or untested."""
    results: list[NodeResult] = []
    for node in root.walk():
        results.append(_evaluate_node(root, node, values_a, values_b))
    return results


def _untested(node: TreeNode, detail: str) -> NodeResult:
    return NodeResult(node.id, node.statement, "untested", detail)


def _evaluate_node(
    root: TreeNode, node: TreeNode, a: Mapping[str, float], b: Mapping[str, float]
) -> NodeResult:
    if node.test is None:
        return _untested(node, "no test is attached to this node")
    kind = node.test["kind"]
    if kind == "share_of_gap":
        return _share_of_gap(root, node, a, b)
    return _rate_gap(node, a, b)


def _share_of_gap(
    root: TreeNode, node: TreeNode, a: Mapping[str, float], b: Mapping[str, float]
) -> NodeResult:
    assert node.test is not None
    parent = _parent_of(root, node)
    if parent is None or parent.combine is None:
        return _untested(node, "share_of_gap needs a parent that combines its children")
    metrics = [c.metric or "" for c in parent.children]
    missing = [m for m in metrics if m not in a or m not in b]
    if missing:
        return _untested(node, f"no value for {', '.join(missing)}")
    threshold = float(node.test.get("min_share", 0.5))
    base = {c.id: a[c.metric or ""] for c in parent.children}
    comp = {c.id: b[c.metric or ""] for c in parent.children}
    if parent.combine == "product":
        shares = shapley_bridge(base, comp).shares()
    elif parent.combine == "sum":
        gap = sum(comp.values()) - sum(base.values())
        shares = {k: (comp[k] - base[k]) / gap if gap else math.nan for k in base}
    else:
        first, second = parent.children[0].id, parent.children[1].id
        shares = shapley_bridge(base, comp, lambda f: f[first] / f[second]).shares()
    share = shares[node.id]
    if math.isnan(share):
        return _untested(node, "there is no gap to share")
    detail = f"{share:.1%} of the gap (threshold {threshold:.0%}; Shapley split)"
    status: Status = "supported" if share >= threshold else "refuted"
    return NodeResult(node.id, node.statement, status, detail, share)


def _rate_gap(node: TreeNode, a: Mapping[str, float], b: Mapping[str, float]) -> NodeResult:
    assert node.test is not None
    num, den = node.test.get("numerator"), node.test.get("denominator")
    if not num or not den:
        return _untested(node, "rate_gap needs numerator and denominator")
    missing = [m for m in (num, den) if m not in a or m not in b]
    if missing:
        return _untested(node, f"no value for {', '.join(missing)}")
    direction = node.test.get("direction", "lower")
    if direction not in ("lower", "higher"):
        return _untested(node, f"direction must be lower or higher; got {direction!r}")
    alpha = float(node.test.get("alpha", 0.05))
    min_effect = float(node.test.get("min_effect", 0.2))
    x1, n1, x2, n2 = (int(round(v)) for v in (a[num], a[den], b[num], b[den]))
    try:
        z = two_proportion_ztest(x1, n1, x2, n2)
    except ValueError as exc:
        return _untested(node, f"cannot test: {exc}")
    claimed_down = direction == "lower"
    if z.p_value < alpha:
        right_way = (z.diff < 0) == claimed_down
        verb = "is" if right_way else "is not"
        detail = (
            f"rate {z.p1:.2%} -> {z.p2:.2%} (diff {z.diff:+.2%}, p = {z.p_value:.3g}); "
            f"the gap {verb} in the claimed direction ({direction})"
        )
        return NodeResult(node.id, node.statement, "supported" if right_way else "refuted",
                          detail, z.diff)

    p1 = z.p1
    p2 = p1 * (1 - min_effect) if claimed_down else p1 * (1 + min_effect)
    n = min(n1, n2)
    if 0 < p1 < 1 and 0 < p2 < 1 and n > 0:
        power = power_two_proportions(p1, p2, n, alpha=alpha)
    else:
        power = 0.0
    if power >= 0.8:
        detail = (
            f"no difference as large as {min_effect:.0%} (rate {z.p1:.2%} -> {z.p2:.2%}, "
            f"p = {z.p_value:.3g}); power to detect it was {power:.0%}"
        )
        return NodeResult(node.id, node.statement, "refuted", detail, z.diff)
    detail = (
        f"not significant (p = {z.p_value:.3g}) and underpowered: power to detect a "
        f"{min_effect:.0%} change is {power:.0%}, below 80%"
    )
    return NodeResult(node.id, node.statement, "untested", detail, z.diff)
