from __future__ import annotations

from app.models import ExtractedInsight


def edit_insights(insights: list[ExtractedInsight]) -> list[ExtractedInsight]:
    edited = []
    accepted_count = 0
    for insight in insights:
        has_quality = bool(
            insight.mechanism
            and insight.intuition_update
            and insight.evidence
            and (insight.mental_model or insight.design_law or insight.failure_mode or insight.eval_pattern or insight.strategy_implication)
        )
        high_accept = (
            insight.mental_model_impact == "high"
            and insight.confidence != "low"
            and insight.novelty != "low"
        )
        medium_accept = (
            insight.mental_model_impact == "medium"
            and insight.novelty == "high"
            and insight.confidence in {"medium", "high"}
        )
        if insight.status == "rejected" or not has_quality:
            insight.status = "rejected"
            insight.discard_reason = insight.discard_reason or "Missing mechanism, intuition update, evidence, or reusable mental model/law/failure/eval/strategy model."
            insight.editor_notes = "Rejected by mocked editor quality bar."
        elif accepted_count < 3 and (high_accept or medium_accept):
            insight.status = "accepted"
            insight.editor_notes = "Accepted by mocked editor scoring rules."
            accepted_count += 1
        elif insight.mental_model_impact == "high" and insight.confidence == "low":
            insight.status = "needs_human_review"
            insight.editor_notes = "High impact but weak confidence."
        else:
            insight.status = "rejected"
            insight.discard_reason = "Did not meet acceptance scoring threshold."
            insight.editor_notes = "Rejected by mocked editor scoring rules."
        edited.append(ExtractedInsight.model_validate(insight.model_dump()))
    return edited
