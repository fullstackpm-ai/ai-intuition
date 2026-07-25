from __future__ import annotations

from app.llm.client import LLMClient, MockLLMClient, parse_jsonish
from app.llm.prompts import EXTRACTION_PROMPT
from app.models import Evidence, ExtractedInsight, NormalizedItem
from app.time import now_utc


def extract_insights(item: NormalizedItem, client: LLMClient | None = None) -> list[ExtractedInsight]:
    llm = client or MockLLMClient()
    prompt = EXTRACTION_PROMPT.format(lane=item.lane, title=item.title, text=item.text)
    payload = parse_jsonish(llm.complete_json(prompt))
    insights = []
    for index, raw in enumerate(payload if isinstance(payload, list) else []):
        status = "candidate"
        if raw.get("discard_reason"):
            status = "rejected"
        evidence = [Evidence.model_validate(entry) for entry in raw.get("evidence", [])]
        insights.append(
            ExtractedInsight(
                id=f"{item.id}_insight_{index}",
                item_id=item.id,
                source_id=item.source_id,
                source_title=item.title,
                source_url=item.url,
                lane=item.lane,
                status=status,
                claim=raw.get("claim", ""),
                mechanism=raw.get("mechanism") or "",
                intuition_update=raw.get("intuition_update") or "",
                mental_model=raw.get("mental_model"),
                design_law=raw.get("design_law") or raw.get("commercial_design_law"),
                failure_mode=raw.get("failure_mode"),
                eval_pattern=raw.get("eval_pattern"),
                boundary_conditions=raw.get("boundary_conditions"),
                counterargument=raw.get("counterargument"),
                strategy_implication=raw.get("strategy_implication"),
                learning_experiment=raw.get("learning_experiment") or raw.get("experiment_30_day"),
                intuition_drill=raw.get("intuition_drill"),
                open_question=raw.get("open_question"),
                evidence=evidence,
                confidence=raw.get("confidence", "low"),
                novelty=raw.get("novelty", "low"),
                mental_model_impact=raw.get("mental_model_impact") or raw.get("decision_impact", "low"),
                discard_reason=raw.get("discard_reason"),
                created_at=now_utc(),
            )
        )
    return insights
