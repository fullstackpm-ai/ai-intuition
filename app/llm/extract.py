from __future__ import annotations

from pathlib import Path

from app.llm.client import LLMClient, MockLLMClient, parse_jsonish
from app.llm.prompts import EXTRACTION_PROMPT
from app.models import Evidence, ExtractedInsight, ExtractionMethod, NormalizedItem
from app.store.files import read_json, read_markdown
from app.time import now_utc


def extract_insights(
    item: NormalizedItem,
    client: LLMClient | None = None,
    extraction_method: ExtractionMethod = "mock",
    extraction_model: str | None = None,
    extraction_notes: str | None = None,
) -> list[ExtractedInsight]:
    llm = client or MockLLMClient()
    prompt = EXTRACTION_PROMPT.format(lane=item.lane, title=item.title, text=item.text)
    payload = parse_jsonish(llm.complete_json(prompt))
    return insights_from_payload(
        item,
        payload,
        extraction_method=extraction_method,
        extraction_model=extraction_model or llm.__class__.__name__,
        extraction_notes=extraction_notes,
    )


def import_insights_from_json(
    item: NormalizedItem,
    path: Path,
    extraction_method: ExtractionMethod = "codex_packet",
    extraction_model: str | None = "codex",
    extraction_notes: str | None = None,
) -> list[ExtractedInsight]:
    return insights_from_payload(
        item,
        read_json(path),
        extraction_method=extraction_method,
        extraction_model=extraction_model,
        extraction_notes=extraction_notes or f"Imported from {path}",
    )


def load_insight_artifacts(data_dir: Path) -> list[ExtractedInsight]:
    normalized_metadata = _normalized_metadata_by_item(data_dir / "normalized")
    insights = []
    for section in ["extracted", "rejected"]:
        for path in sorted((data_dir / section).glob("*.json")):
            payload = read_json(path)
            if not isinstance(payload, list):
                raise ValueError(f"Extraction artifact must be a JSON list: {path}")
            for raw in payload:
                if not isinstance(raw, dict):
                    raise ValueError(f"Extraction artifact entries must be JSON objects: {path}")
                enriched = _with_normalized_metadata(raw, normalized_metadata)
                insights.append(ExtractedInsight.model_validate(enriched))
    return insights


def insights_from_payload(
    item: NormalizedItem,
    payload: object,
    extraction_method: ExtractionMethod,
    extraction_model: str | None = None,
    extraction_notes: str | None = None,
) -> list[ExtractedInsight]:
    if not isinstance(payload, list):
        raise ValueError("Extraction payload must be a JSON list of insight objects.")
    insights = []
    for index, raw in enumerate(payload):
        if not isinstance(raw, dict):
            raise ValueError("Each extracted insight must be a JSON object.")
        status = "candidate"
        if raw.get("discard_reason"):
            status = "rejected"
        if raw.get("status"):
            status = str(raw["status"])
        evidence = [Evidence.model_validate(entry) for entry in raw.get("evidence", [])]
        insights.append(
            ExtractedInsight(
                id=str(raw.get("id") or f"{item.id}_insight_{index}"),
                item_id=str(raw.get("item_id") or item.id),
                source_id=str(raw.get("source_id") or item.source_id),
                source_name=raw.get("source_name") or item.source_name,
                source_type=raw.get("source_type") or item.source_type,
                source_title=str(raw.get("source_title") or item.title),
                source_url=raw.get("source_url") or item.url,
                raw_artifact_id=raw.get("raw_artifact_id") or item.raw_artifact_id,
                raw_path=raw.get("raw_path") or item.raw_path,
                normalized_path=raw.get("normalized_path") or item.normalized_path,
                published_at=raw.get("published_at") or item.published_at,
                lane=str(raw.get("lane") or item.lane),
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
                editor_notes=raw.get("editor_notes"),
                discard_reason=raw.get("discard_reason"),
                extraction_method=extraction_method,
                extraction_model=extraction_model,
                extraction_notes=extraction_notes,
                source_references=raw.get("source_references") or [],
                created_at=raw.get("created_at") or now_utc(),
            )
        )
    return insights


def _normalized_metadata_by_item(normalized_dir: Path) -> dict[str, dict[str, object]]:
    metadata_by_item = {}
    for path in sorted(normalized_dir.glob("*.md")):
        metadata, _ = read_markdown(path)
        item_id = str(metadata.get("id") or path.stem)
        metadata_by_item[item_id] = {
            "item_id": item_id,
            "source_id": metadata.get("source_id"),
            "source_name": metadata.get("source_name"),
            "source_type": metadata.get("source_type"),
            "source_title": metadata.get("title"),
            "source_url": metadata.get("url"),
            "raw_artifact_id": metadata.get("raw_artifact_id"),
            "raw_path": metadata.get("raw_path"),
            "normalized_path": _portable_path(path),
            "published_at": metadata.get("published_at"),
            "lane": metadata.get("lane"),
        }
    return metadata_by_item


def _with_normalized_metadata(raw: dict[str, object], normalized_metadata: dict[str, dict[str, object]]) -> dict[str, object]:
    enriched = dict(raw)
    item_id = str(enriched.get("item_id") or "")
    metadata = normalized_metadata.get(item_id, {})
    for field in [
        "source_name",
        "source_type",
        "raw_artifact_id",
        "raw_path",
        "normalized_path",
        "published_at",
    ]:
        if not enriched.get(field) and metadata.get(field):
            enriched[field] = metadata[field]
    for field in ["source_id", "source_title", "source_url", "lane"]:
        if not enriched.get(field) and metadata.get(field):
            enriched[field] = metadata[field]
    if not enriched.get("created_at"):
        enriched["created_at"] = now_utc()
    return enriched


def _portable_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def build_extraction_packet(item: NormalizedItem) -> str:
    schema_hint = """
Return a JSON list of extracted insight objects.

Required for each kept insight:
- claim
- mechanism
- intuition_update
- at least one of mental_model, design_law, failure_mode, eval_pattern, or strategy_implication
- evidence: [{quote, location, note}]
- confidence: low | medium | high
- novelty: low | medium | high
- mental_model_impact: low | medium | high

Use status `rejected` with `discard_reason` when the source does not contain a durable insight.
Rejected items may omit mechanism and evidence, but the discard reason must be specific.
""".strip()
    quality_bar = """
A useful insight is not a summary. It must identify a mechanism and say what the reader should now believe differently.
Prefer one to three durable insights over broad coverage.
Preserve source traceability with evidence quotes and locations.
Reject generic summaries even when the source is interesting.
""".strip()
    return "\n\n".join(
        [
            f"# Extraction Packet: {item.title}",
            "## Output paths",
            f"- Accepted/candidate insights: `data/extracted/{item.id}.json`",
            f"- Rejected insights: `data/rejected/{item.id}.json`",
            "## Source metadata",
            f"- item_id: `{item.id}`",
            f"- source_id: `{item.source_id}`",
            f"- source_name: `{item.source_name}`",
            f"- source_type: `{item.source_type}`",
            f"- lane: `{item.lane}`",
            f"- title: `{item.title}`",
            f"- url: `{item.url}`",
            f"- published_at: `{item.published_at}`",
            f"- raw_artifact_id: `{item.raw_artifact_id}`",
            f"- raw_path: `{item.raw_path}`",
            f"- normalized_path: `{item.normalized_path}`",
            f"- detected_page_type: `{item.detected_page_type}`",
            f"- primary_content_kind: `{item.primary_content_kind}`",
            f"- quality_status: `{item.quality_status}`",
            f"- quality_flags: `{item.quality_flags}`",
            f"- degraded_reason: `{item.degraded_reason}`",
            "## Schema guidance",
            schema_hint,
            "## Quality bar",
            quality_bar,
            "## Extraction prompt",
            EXTRACTION_PROMPT.format(lane=item.lane, title=item.title, text=item.text),
        ]
    )
