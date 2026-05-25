from __future__ import annotations

from app.models import ExtractedInsight


def edit_insights(insights: list[ExtractedInsight]) -> list[ExtractedInsight]:
    edited = []
    accepted_count = 0
    for insight in insights:
        has_quality = bool(
            insight.mechanism
            and insight.ender_implication
            and insight.experiment_30_day
            and insight.evidence
            and (insight.commercial_design_law or insight.failure_mode)
        )
        high_accept = (
            insight.decision_impact == "high"
            and insight.confidence != "low"
            and insight.novelty != "low"
        )
        medium_accept = (
            insight.decision_impact == "medium"
            and insight.novelty == "high"
            and insight.confidence in {"medium", "high"}
        )
        if insight.status == "rejected" or not has_quality:
            insight.status = "rejected"
            insight.discard_reason = insight.discard_reason or "Missing mechanism, Ender implication, falsifiable experiment, evidence, or reusable law."
            insight.editor_notes = "Rejected by mocked editor quality bar."
        elif accepted_count < 3 and (high_accept or medium_accept):
            insight.status = "accepted"
            insight.editor_notes = "Accepted by mocked editor scoring rules."
            accepted_count += 1
        elif insight.decision_impact == "high" and insight.confidence == "low":
            insight.status = "needs_human_review"
            insight.editor_notes = "High impact but weak confidence."
        else:
            insight.status = "rejected"
            insight.discard_reason = "Did not meet acceptance scoring threshold."
            insight.editor_notes = "Rejected by mocked editor scoring rules."
        edited.append(ExtractedInsight.model_validate(insight.model_dump()))
    return edited
