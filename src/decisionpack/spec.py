"""The analysis spec: one YAML file that says what to compare and what to ask about it."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MetricSpec(_Strict):
    """The headline metric is ``sum(numerator) / sum(denominator)`` over the rows of a group."""

    name: str
    label: str
    numerator: str
    denominator: str
    unit: str = ""
    lower_is_better: bool = True
    decimals: int = Field(default=2, ge=0, le=8)


class GroupsSpec(_Strict):
    column: str
    baseline: str
    comparison: str
    baseline_label: str | None = None
    comparison_label: str | None = None


class FactorSpec(_Strict):
    """One factor of the metric: ``sum(numerator) / sum(denominator)``."""

    name: str
    label: str | None = None
    description: str | None = None
    numerator: str
    denominator: str


class BridgeSpec(_Strict):
    """Factors are ratios of sums. ``formula`` says how they combine into the metric; the default
    is their product, which is right when the ratios telescope (spend/impressions x ...)."""

    factors: list[FactorSpec] = Field(min_length=1)
    formula: str | None = None


class SegmentsSpec(_Strict):
    dimensions: list[str] = Field(min_length=1)
    numerator: str
    denominator: str
    label: str = "rate"
    min_denominator: float = Field(default=100, ge=0)
    alpha: float = Field(default=0.05, gt=0, lt=1)
    correction: Literal["bh", "holm"] = "bh"
    simpson_stratifiers: list[str] = Field(default_factory=list)


class AssumptionSpec(_Strict):
    name: str
    low: float
    base: float
    high: float
    source: str


class ScoringSpec(_Strict):
    method: Literal["ice", "rice"]
    impact: float
    confidence: float
    ease: float | None = None
    reach: float | None = None
    effort: float | None = None


class RecommendationSpec(_Strict):
    id: str
    title: str
    rationale: str
    impact_formula: str
    impact_unit: str
    assumptions: list[AssumptionSpec] = Field(default_factory=list)
    scoring: ScoringSpec


class ContextSpec(_Strict):
    """Optional wording for the SCQA summary. Anything left out is built from the results."""

    situation: str | None = None
    complication: str | None = None
    question: str | None = None


class Spec(_Strict):
    title: str
    metric: MetricSpec
    groups: GroupsSpec
    bridge: BridgeSpec
    derived_columns: dict[str, str] = Field(default_factory=dict)
    filter: str | None = None
    measures: dict[str, str] = Field(default_factory=dict)
    segments: SegmentsSpec | None = None
    tree: dict[str, Any] | None = None
    tree_file: str | None = None
    recommendations: list[RecommendationSpec] = Field(default_factory=list)
    context: ContextSpec = Field(default_factory=ContextSpec)
    data_notes: list[str] = Field(default_factory=list)
    observational: bool = True
    n_boot: int = Field(default=1000, ge=100, le=20000)
    seed: int = 0

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be blank")
        return v

    @model_validator(mode="after")
    def _one_tree_source(self) -> Spec:
        if self.tree is not None and self.tree_file is not None:
            raise ValueError("give either tree or tree_file, not both")
        names = [f.name for f in self.bridge.factors]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate factor names in bridge: {names}")
        return self


class SpecError(ValueError):
    pass


def parse_spec(data: Any) -> Spec:
    """Build a Spec from already-parsed YAML, turning pydantic errors into one readable message."""
    from pydantic import ValidationError

    if not isinstance(data, dict):
        raise SpecError("the spec must be a YAML mapping")
    try:
        return Spec.model_validate(data)
    except ValidationError as exc:
        lines = []
        for err in exc.errors():
            where = ".".join(str(p) for p in err["loc"]) or "spec"
            lines.append(f"{where}: {err['msg']}")
        raise SpecError("invalid spec:\n  " + "\n  ".join(lines)) from exc


def load_spec(path: str | Path) -> Spec:
    p = Path(path)
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SpecError(f"invalid YAML in {p}: {exc}") from exc
    return parse_spec(data)
