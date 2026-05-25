from __future__ import annotations

from app.ids import content_hash
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
                id=f"{item.id}_insight_{index}_{content_hash(str(raw))[:8]}",
                item_id=item.id,
                source_id=item.source_id,
                source_title=item.title,
                source_url=item.url,
                lane=item.lane,
                status=status,
                claim=raw.get("claim", ""),
                mechanism=raw.get("mechanism") or "",
                commercial_design_law=raw.get("commercial_design_law"),
                failure_mode=raw.get("failure_mode"),
                eval_pattern=raw.get("eval_pattern"),
                ender_implication=raw.get("ender_implication"),
                experiment_30_day=raw.get("experiment_30_day"),
                evidence=evidence,
                confidence=raw.get("confidence", "low"),
                novelty=raw.get("novelty", "low"),
                decision_impact=raw.get("decision_impact", "low"),
                discard_reason=raw.get("discard_reason"),
                created_at=now_utc(),
            )
        )
    return insights
