from app.llm.edit import edit_insights
from app.llm.extract import extract_insights
from app.models import NormalizedItem


def test_extract_returns_valid_json_models_for_golden_note() -> None:
    item = NormalizedItem(
        id="item",
        raw_artifact_id="raw",
        source_id="manual",
        lane="manual",
        title="Prompt Design Principles",
        normalized_path="data/normalized/item.md",
        text="Prompt instructions are attention architecture. Business-critical rules need tools, code, validators, permissions, and workflow state because finite attention makes prompt compliance probabilistic.",
        word_count=20,
    )
    insights = extract_insights(item)
    assert insights
    assert insights[0].mechanism
    assert insights[0].intuition_update
    assert insights[0].evidence
    assert insights[0].mental_model or insights[0].design_law or insights[0].failure_mode or insights[0].eval_pattern or insights[0].strategy_implication


def test_generic_summaries_are_rejected() -> None:
    item = NormalizedItem(
        id="generic",
        raw_artifact_id="raw",
        source_id="manual",
        lane="manual",
        title="Generic AI News",
        normalized_path="data/normalized/generic.md",
        text="This source says AI is moving fast and companies are launching products.",
        word_count=12,
    )
    edited = edit_insights(extract_insights(item))
    assert edited[0].status == "rejected"
    assert "Generic summary" in (edited[0].discard_reason or "")
