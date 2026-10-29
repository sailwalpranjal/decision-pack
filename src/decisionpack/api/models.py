"""Typed request and response models. They mirror ``serialize.result_to_dict``."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

JobState = Literal["queued", "running", "done", "failed"]


class RunCreated(BaseModel):
    id: str
    status: JobState
    status_url: str


class RunStatus(BaseModel):
    id: str
    status: JobState
    created_at: datetime
    error: str | None = None


class MetricOut(BaseModel):
    name: str
    label: str
    unit: str
    lower_is_better: bool
    baseline: float
    comparison: float
    gap: float
    ratio: float | None
    gap_ci: list[float | None] = Field(description="95% bootstrap interval for the gap")


class GroupsOut(BaseModel):
    baseline: str
    comparison: str
    n_baseline: int
    n_comparison: int


class WaterfallStep(BaseModel):
    label: str
    start: float
    end: float
    delta: float


class OrderSensitivityOut(BaseModel):
    n_orders: int
    min_share: dict[str, float | None]
    max_share: dict[str, float | None]


class BridgeOut(BaseModel):
    factors: list[str]
    baseline_factors: dict[str, float]
    comparison_factors: dict[str, float]
    shapley: dict[str, float]
    shapley_shares: dict[str, float | None]
    sequential: dict[str, float]
    sequential_order: list[str]
    waterfall: list[WaterfallStep]
    order_sensitivity: OrderSensitivityOut | None


class SegmentRowOut(BaseModel):
    dimension: str
    value: str
    rate_a: float
    rate_b: float
    diff: float
    contribution: float
    rate_effect: float
    mix_effect: float
    p_value: float
    p_holm: float | None
    p_bh: float | None
    significant: bool


class ExcludedOut(BaseModel):
    dimension: str
    value: str
    reason: str


class SimpsonOut(BaseModel):
    stratifier: str
    overall_diff: float
    reversed: bool
    message: str


class SegmentsOut(BaseModel):
    rate_baseline: float
    rate_comparison: float
    gap: float
    alpha: float
    correction: str
    family_size: int
    rows: list[SegmentRowOut]
    excluded: list[ExcludedOut]
    simpson: list[SimpsonOut]


class TreeNodeOut(BaseModel):
    node_id: str
    statement: str
    status: Literal["supported", "refuted", "untested"]
    detail: str
    statistic: float | None


class MeceProblemOut(BaseModel):
    node_id: str
    message: str


class TreeOut(BaseModel):
    results: list[TreeNodeOut]
    mece_problems: list[MeceProblemOut]


class AssumptionOut(BaseModel):
    name: str
    low: float
    base: float
    high: float
    source: str


class SensitivityOut(BaseModel):
    name: str
    at_low: float
    at_high: float
    swing: float


class RecommendationOut(BaseModel):
    rank: int
    id: str
    title: str
    rationale: str
    impact_unit: str
    low: float
    base: float
    high: float
    score: float
    arithmetic: str
    assumptions: list[AssumptionOut]
    sensitivity: list[SensitivityOut]
    warnings: list[str]


class ResultOut(BaseModel):
    title: str
    observational: bool
    metric: MetricOut
    groups: GroupsOut
    bridge: BridgeOut
    segments: SegmentsOut | None
    tree: TreeOut | None
    recommendations: list[RecommendationOut]
    warnings: list[str]


class ErrorOut(BaseModel):
    detail: str
