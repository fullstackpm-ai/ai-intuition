from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.llm.extract import build_extraction_packet, extract_insights, import_insights_from_json
from app.llm.synthesize import build_weekly_brief
from app.models import Evidence, ExtractedInsight, NormalizedItem
from app.store.files import read_markdown, write_json


def _item() -> NormalizedItem:
    return NormalizedItem(
        id="codex_loop",
        raw_artifact_id="raw",
        source_id="openai_research",
        lane="product_patterns",
        title="Unrolling the Codex agent loop",
        url="https://openai.com/index/unrolling-the-codex-agent-loop/",
        normalized_path="data/normalized/codex_loop.md",
        text="Prompt instructions are attention architecture. Business-critical rules need tools, code, validators, permissions, and workflow state because finite attention makes prompt compliance probabilistic.",
        word_count=20,
    )


def test_mock_extraction_records_mock_provenance() -> None:
    insights = extract_insights(_item())

    assert insights
    assert insights[0].extraction_method == "mock"
    assert insights[0].extraction_model == "MockLLMClient"


def test_extraction_packet_contains_schema_quality_bar_and_output_paths() -> None:
    packet = build_extraction_packet(_item())

    assert "data/extracted/codex_loop.json" in packet
    assert "data/rejected/codex_loop.json" in packet
    assert "## Quality bar" in packet
    assert "evidence: [{quote, location, note}]" in packet
    assert "Unrolling the Codex agent loop" in packet


def test_imported_codex_extraction_validates_and_sets_provenance(tmp_path) -> None:
    path = tmp_path / "codex_loop.json"
    write_json(
        path,
        [
            {
                "status": "accepted",
                "claim": "Agents are managed execution loops, not prompts with tools.",
                "mechanism": "The harness repeatedly builds context, invokes the model, executes tool calls, appends observations, and manages termination.",
                "intuition_update": "Treat the commercial product as the loop around model cognition, not just the model response.",
                "mental_model": "Agent = model + context builder + tool registry + execution environment + observation stream + termination condition.",
                "design_law": "The harness is the product.",
                "boundary_conditions": "Most important for multi-step workflows with tools and mutable state.",
                "evidence": [
                    {
                        "quote": "Tool outputs are appended back into later prompts.",
                        "location": "agent loop section",
                        "note": "Shows the observation loop.",
                    }
                ],
                "confidence": "high",
                "novelty": "high",
                "mental_model_impact": "high",
            }
        ],
    )

    insights = import_insights_from_json(_item(), path)

    assert len(insights) == 1
    assert insights[0].status == "accepted"
    assert insights[0].extraction_method == "codex_packet"
    assert insights[0].extraction_model == "codex"
    assert insights[0].source_url == "https://openai.com/index/unrolling-the-codex-agent-loop/"


def test_imported_real_extraction_requires_evidence_location(tmp_path) -> None:
    path = tmp_path / "bad.json"
    write_json(
        path,
        [
            {
                "status": "accepted",
                "claim": "Agents are loops.",
                "mechanism": "The harness repeats model calls and tool calls.",
                "intuition_update": "Think in loops.",
                "mental_model": "Agent = loop.",
                "evidence": [{"quote": "Loop evidence without location."}],
                "confidence": "high",
                "novelty": "high",
                "mental_model_impact": "high",
            }
        ],
    )

    with pytest.raises(ValidationError, match="evidence location"):
        import_insights_from_json(_item(), path)


def test_weekly_brief_records_extraction_provenance(tmp_path) -> None:
    insights = [
        ExtractedInsight(
            id="codex_loop_insight_0",
            item_id="codex_loop",
            source_id="openai_research",
            source_title="Unrolling the Codex agent loop",
            source_url="https://openai.com/index/unrolling-the-codex-agent-loop/",
            lane="product_patterns",
            status="accepted",
            claim="Agents are managed execution loops.",
            mechanism="The harness repeats model calls, tool calls, observations, and termination checks.",
            intuition_update="Think of agents as runtimes.",
            mental_model="Agent = model plus harness.",
            evidence=[Evidence(quote="Loop evidence.", location="agent loop section")],
            confidence="high",
            novelty="high",
            mental_model_impact="high",
            extraction_method="codex_packet",
            extraction_model="codex",
            created_at=datetime.now(UTC),
        ),
        ExtractedInsight(
            id="mock_insight_0",
            item_id="mock",
            source_id="manual",
            source_title="Mock",
            lane="manual",
            status="accepted",
            claim="Prompt rules are probabilistic.",
            mechanism="Finite attention makes prompt compliance probabilistic.",
            intuition_update="Treat prompts as attention architecture.",
            mental_model="Prompting is attention architecture.",
            evidence=[Evidence(quote="Prompt instructions are attention architecture.")],
            confidence="high",
            novelty="high",
            mental_model_impact="high",
            extraction_method="mock",
            extraction_model="MockLLMClient",
            created_at=datetime.now(UTC),
        ),
    ]

    _, path = build_weekly_brief("2026-W30", insights, tmp_path)
    metadata, body = read_markdown(path)

    assert metadata["extraction_provenance"] == {"codex_packet": 1, "mock": 1}
    assert "mock extraction provenance" in metadata["extraction_warning"]
    assert "## Extraction provenance" in body
    assert "codex_packet: 1" in body
    assert "mock: 1" in body
