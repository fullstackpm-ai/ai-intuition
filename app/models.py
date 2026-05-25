from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


Lane = Literal[
    "frontier_primitives",
    "reliability_failures",
    "product_patterns",
    "frontier_priors",
    "strategy_value_capture",
    "manual",
]


class Source(BaseModel):
    id: str
    name: str
    lane: Lane
    type: str
    urls: list[str] = Field(default_factory=list)
    path: str | None = None
    enabled: bool = True
    transcript_provider: str | None = None
    notes: str | None = None


class SourceRegistry(BaseModel):
    sources: list[Source]


class RawArtifact(BaseModel):
    id: str
    source_id: str
    source_name: str
    lane: str
    source_type: str
    title: str
    url: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    discovered_at: datetime
    raw_path: str
    content_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedItem(BaseModel):
    id: str
    raw_artifact_id: str
    source_id: str
    lane: str
    title: str
    url: str | None = None
    published_at: datetime | None = None
    normalized_path: str
    text: str
    word_count: int
    extraction_notes: str | None = None


class Evidence(BaseModel):
    quote: str
    location: str | None = None
    note: str | None = None


class ExtractedInsight(BaseModel):
    id: str
    item_id: str
    source_id: str
    source_title: str
    source_url: str | None = None
    lane: str
    status: Literal["candidate", "accepted", "rejected", "needs_human_review"]
    claim: str
    mechanism: str
    commercial_design_law: str | None = None
    failure_mode: str | None = None
    eval_pattern: str | None = None
    ender_implication: str | None = None
    experiment_30_day: str | None = None
    evidence: list[Evidence]
    confidence: Literal["low", "medium", "high"]
    novelty: Literal["low", "medium", "high"]
    decision_impact: Literal["low", "medium", "high"]
    editor_notes: str | None = None
    discard_reason: str | None = None
    created_at: datetime

    @model_validator(mode="after")
    def accepted_insights_have_quality_bar(self) -> "ExtractedInsight":
        if self.status == "accepted":
            missing = []
            if not self.mechanism:
                missing.append("mechanism")
            if not (self.commercial_design_law or self.failure_mode):
                missing.append("design law or failure mode")
            if not self.ender_implication:
                missing.append("Ender implication")
            if not self.experiment_30_day:
                missing.append("experiment")
            if not self.evidence:
                missing.append("evidence")
            if missing:
                raise ValueError(f"accepted insight missing: {', '.join(missing)}")
        return self


class WeeklyBrief(BaseModel):
    week: str
    generated_at: datetime
    one_line_thesis: str
    belief_updates: list[str]
    new_or_updated_design_laws: list[str]
    new_failure_modes: list[str]
    ender_implications: dict[str, list[str]]
    experiments: list[str]
    ignored_noise: list[str]
    source_rollup: list[str]
    human_review_flags: list[str]
