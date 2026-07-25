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
    priority: str | None = None
    source_url: str | None = None
    rss_url: str | None = None
    rss_url_env: str | None = None
    youtube_url: str | None = None
    adapter: str | None = None
    extraction_goal: str | None = None
    include_topics: list[str] = Field(default_factory=list)
    discard_if: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    path: str | None = None
    enabled: bool = True
    transcript_provider: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def populate_urls_from_source_fields(self) -> "Source":
        urls = list(self.urls)
        for candidate in [self.rss_url, self.source_url, self.youtube_url]:
            if candidate and candidate not in urls:
                urls.append(candidate)
        self.urls = urls
        return self


class SourceRegistry(BaseModel):
    version: int | None = None
    sources: list[Source]
    tooling: list[dict[str, Any]] = Field(default_factory=list)
    deferred_sources: list[dict[str, Any]] = Field(default_factory=list)


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
    intuition_update: str = ""
    mental_model: str | None = None
    design_law: str | None = None
    failure_mode: str | None = None
    eval_pattern: str | None = None
    boundary_conditions: str | None = None
    counterargument: str | None = None
    strategy_implication: str | None = None
    learning_experiment: str | None = None
    intuition_drill: str | None = None
    open_question: str | None = None
    evidence: list[Evidence]
    confidence: Literal["low", "medium", "high"]
    novelty: Literal["low", "medium", "high"]
    mental_model_impact: Literal["low", "medium", "high"] = "low"
    editor_notes: str | None = None
    discard_reason: str | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        migrated = dict(data)
        if not migrated.get("design_law") and migrated.get("commercial_design_law"):
            migrated["design_law"] = migrated["commercial_design_law"]
        if not migrated.get("learning_experiment") and migrated.get("experiment_30_day"):
            migrated["learning_experiment"] = migrated["experiment_30_day"]
        if not migrated.get("mental_model_impact") and migrated.get("decision_impact"):
            migrated["mental_model_impact"] = migrated["decision_impact"]
        if not migrated.get("intuition_update") and migrated.get("claim"):
            migrated["intuition_update"] = migrated["claim"]
        return migrated

    @model_validator(mode="after")
    def accepted_insights_have_quality_bar(self) -> "ExtractedInsight":
        if self.status == "accepted":
            missing = []
            if not self.mechanism:
                missing.append("mechanism")
            if not self.intuition_update:
                missing.append("intuition update")
            if not (self.mental_model or self.design_law or self.failure_mode or self.eval_pattern or self.strategy_implication):
                missing.append("mental model, design law, failure mode, eval pattern, or strategy implication")
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
    new_or_updated_mental_models: list[str]
    new_or_updated_design_laws: list[str]
    new_failure_modes: list[str]
    new_eval_patterns: list[str]
    strategy_updates: list[str]
    learning_experiments: list[str]
    intuition_drills: list[str]
    ignored_noise: list[str]
    source_rollup: list[str]
    human_review_flags: list[str]
