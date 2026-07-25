from datetime import UTC, datetime

from app.llm.belief_update import update_beliefs
from app.models import Evidence, ExtractedInsight


def test_belief_update_is_idempotent_with_existing_week(tmp_path) -> None:
    insight = ExtractedInsight(
        id="insight",
        item_id="item",
        source_id="manual",
        source_title="Prompt Design",
        lane="manual",
        status="accepted",
        claim="Rules in prose are probabilistic.",
        mechanism="Finite attention makes prompt compliance probabilistic.",
        intuition_update="Treat the model as an interpreter, not the enforcement layer.",
        mental_model="Prompting is attention architecture.",
        design_law="Business-critical rules should be structural.",
        evidence=[Evidence(quote="Prompt instructions are attention architecture.")],
        confidence="high",
        novelty="high",
        mental_model_impact="high",
        created_at=datetime.now(UTC),
    )

    first = update_beliefs("2026-W21", [insight], tmp_path)
    second = update_beliefs("2026-W21", [insight], tmp_path)

    assert first
    assert second == []
    ledger = (tmp_path / "belief-ledger.md").read_text()
    assert ledger.count("## 2026-W21") == 1
    assert ledger.count("Treat the model as an interpreter") == 1
