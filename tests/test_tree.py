from __future__ import annotations

import pytest
import yaml

from decisionpack.core.tree import (
    TreeError,
    evaluate_tree,
    load_tree,
    parse_tree,
    validate_mece,
)

# Segment A: cost 8 = 2 * 4. Segment B: cost 27 = 3 * 9. The gap is 19.
VALUES_A = {"cost": 8.0, "cpm": 2.0, "conv": 4.0, "approved": 40.0, "clicks": 1000.0}
VALUES_B = {"cost": 27.0, "cpm": 3.0, "conv": 9.0, "approved": 25.0, "clicks": 1000.0}

TREE_YAML = """
id: gap
statement: Cost per approved conversion is higher for B
metric: cost
combine: product
children:
  - id: media
    statement: Media is more expensive
    metric: cpm
    test: {kind: share_of_gap, min_share: 0.5}
  - id: post_click
    statement: Fewer clicks become approved conversions
    metric: conv
    test: {kind: share_of_gap, min_share: 0.5}
"""


def tree():
    return parse_tree(yaml.safe_load(TREE_YAML))


def test_parse_builds_the_hierarchy():
    t = tree()
    assert t.id == "gap" and [c.id for c in t.children] == ["media", "post_click"]
    assert t.combine == "product"
    assert [n.id for n in t.walk()] == ["gap", "media", "post_click"]


def test_a_tree_that_adds_up_passes_mece():
    assert validate_mece(tree(), VALUES_A, VALUES_B) == []


def test_a_tree_that_does_not_add_up_is_reported_with_the_numbers():
    broken = dict(VALUES_B, conv=10.0)  # 3 * 10 = 30, but cost says 27
    problems = validate_mece(tree(), VALUES_A, VALUES_B | {"conv": 10.0})
    assert len(problems) == 1
    assert problems[0].node_id == "gap"
    assert "27" in problems[0].message and "30" in problems[0].message
    assert broken["conv"] == 10.0


def test_sum_combination():
    data = yaml.safe_load("""
id: total
statement: total revenue
metric: total
combine: sum
children:
  - {id: web, statement: web, metric: web}
  - {id: store, statement: store, metric: store}
""")
    t = parse_tree(data)
    a = {"total": 10.0, "web": 4.0, "store": 6.0}
    b = {"total": 25.0, "web": 5.0, "store": 20.0}
    assert validate_mece(t, a, b) == []
    assert validate_mece(t, a, b | {"store": 21.0})[0].node_id == "total"


def test_ratio_combination():
    data = yaml.safe_load("""
id: rate
statement: purchase rate
metric: rate
combine: ratio
children:
  - {id: buyers, statement: buyers, metric: buyers}
  - {id: sessions, statement: sessions, metric: sessions}
""")
    t = parse_tree(data)
    a = {"rate": 0.1, "buyers": 10.0, "sessions": 100.0}
    b = {"rate": 0.2, "buyers": 40.0, "sessions": 200.0}
    assert validate_mece(t, a, b) == []


def test_share_of_gap_marks_supported_and_refuted_from_shapley_shares():
    res = {r.node_id: r for r in evaluate_tree(tree(), VALUES_A, VALUES_B)}
    # Shapley: media = (3-2)*(4+9)/2 = 6.5, post_click = (9-4)*(2+3)/2 = 12.5, gap 19
    assert res["post_click"].status == "supported"
    assert res["media"].status == "refuted"
    assert res["post_click"].statistic == pytest.approx(12.5 / 19)
    assert res["media"].statistic == pytest.approx(6.5 / 19)
    assert "of the gap" in res["post_click"].detail and "Shapley" in res["post_click"].detail


def test_node_without_a_test_is_untested():
    t = parse_tree(
        yaml.safe_load("""
id: gap
statement: s
metric: cost
combine: product
children:
  - {id: media, statement: m, metric: cpm}
  - {id: post_click, statement: p, metric: conv}
""")
    )
    res = {r.node_id: r.status for r in evaluate_tree(t, VALUES_A, VALUES_B)}
    assert res == {"gap": "untested", "media": "untested", "post_click": "untested"}


RATE_TREE = """
id: gap
statement: root
metric: cost
children:
  - id: conv_rate
    statement: B converts clicks to approvals at a lower rate
    metric: conv
    test: {kind: rate_gap, numerator: approved, denominator: clicks, direction: lower, alpha: 0.05}
"""


def test_rate_gap_supported_when_significant_in_the_claimed_direction():
    a = VALUES_A | {"approved": 90.0, "clicks": 1000.0}
    b = VALUES_B | {"approved": 40.0, "clicks": 1000.0}
    r = {x.node_id: x for x in evaluate_tree(parse_tree(yaml.safe_load(RATE_TREE)), a, b)}
    assert r["conv_rate"].status == "supported"
    assert r["conv_rate"].statistic < 0


def test_rate_gap_refuted_when_significant_in_the_opposite_direction():
    a = VALUES_A | {"approved": 40.0, "clicks": 1000.0}
    b = VALUES_B | {"approved": 90.0, "clicks": 1000.0}
    r = {x.node_id: x for x in evaluate_tree(parse_tree(yaml.safe_load(RATE_TREE)), a, b)}
    assert r["conv_rate"].status == "refuted"


def test_rate_gap_untested_when_not_significant_and_underpowered():
    a = VALUES_A | {"approved": 10.0, "clicks": 100.0}
    b = VALUES_B | {"approved": 8.0, "clicks": 100.0}
    r = {x.node_id: x for x in evaluate_tree(parse_tree(yaml.safe_load(RATE_TREE)), a, b)}
    assert r["conv_rate"].status == "untested"
    assert "power" in r["conv_rate"].detail


def test_rate_gap_refuted_when_not_significant_but_well_powered_for_the_min_effect():
    text = RATE_TREE.replace("alpha: 0.05}", "alpha: 0.05, min_effect: 0.2}")
    a = VALUES_A | {"approved": 1000.0, "clicks": 10000.0}
    b = VALUES_B | {"approved": 1002.0, "clicks": 10000.0}
    r = {x.node_id: x for x in evaluate_tree(parse_tree(yaml.safe_load(text)), a, b)}
    assert r["conv_rate"].status == "refuted"
    assert "no difference as large as" in r["conv_rate"].detail


def test_missing_values_make_a_node_untested_not_an_error():
    a = {k: v for k, v in VALUES_A.items() if k != "conv"}
    res = {r.node_id: r for r in evaluate_tree(tree(), a, VALUES_B)}
    assert res["post_click"].status == "untested"
    assert "conv" in res["post_click"].detail


# ---- structure errors ---------------------------------------------------------------------


def test_duplicate_ids_rejected():
    with pytest.raises(TreeError, match="duplicate"):
        parse_tree({"id": "a", "statement": "s", "children": [{"id": "a", "statement": "t"}]})


def test_missing_fields_rejected():
    with pytest.raises(TreeError, match="id"):
        parse_tree({"statement": "s"})
    with pytest.raises(TreeError, match="statement"):
        parse_tree({"id": "a"})


def test_combine_without_metric_or_children_rejected():
    with pytest.raises(TreeError, match="children"):
        parse_tree({"id": "a", "statement": "s", "metric": "m", "combine": "product"})
    with pytest.raises(TreeError, match="metric"):
        parse_tree(
            {
                "id": "a",
                "statement": "s",
                "combine": "product",
                "children": [{"id": "b", "statement": "t", "metric": "x"}],
            }
        )


def test_unknown_combine_and_test_kind_rejected():
    with pytest.raises(TreeError, match="combine"):
        parse_tree(
            {
                "id": "a",
                "statement": "s",
                "metric": "m",
                "combine": "magic",
                "children": [{"id": "b", "statement": "t", "metric": "x"}],
            }
        )
    with pytest.raises(TreeError, match="kind"):
        parse_tree({"id": "a", "statement": "s", "test": {"kind": "vibes"}})


def test_ratio_needs_exactly_two_children():
    with pytest.raises(TreeError, match="exactly two"):
        parse_tree(
            {
                "id": "a",
                "statement": "s",
                "metric": "m",
                "combine": "ratio",
                "children": [{"id": "b", "statement": "t", "metric": "x"}],
            }
        )


def test_load_tree_from_yaml_text_and_bad_yaml(tmp_path):
    p = tmp_path / "t.yaml"
    p.write_text(TREE_YAML, encoding="utf-8")
    assert load_tree(p).id == "gap"
    p.write_text("- just\n- a list\n", encoding="utf-8")
    with pytest.raises(TreeError, match="mapping"):
        load_tree(p)
    p.write_text("id: [unclosed", encoding="utf-8")
    with pytest.raises(TreeError, match="YAML"):
        load_tree(p)
