from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models import Evidence, ExtractedInsight, Source


def test_source_model_validates_lane() -> None:
    source = Source(id="manual", name="Manual", lane="manual", type="manual")
    assert source.id == "manual"


def test_accepted_insight_requires_quality_bar() -> None:
    with pytest.raises(ValidationError):
        ExtractedInsight(
            id="bad",
            item_id="item",
            source_id="manual",
            source_title="Bad Summary",
            lane="manual",
            status="accepted",
            claim="AI is moving fast.",
            mechanism="",
            evidence=[],
            confidence="low",
            novelty="low",
            decision_impact="low",
            created_at=datetime.now(UTC),
        )


def test_accepted_insight_valid() -> None:
    insight = ExtractedInsight(
        id="good",
        item_id="item",
        source_id="manual",
        source_title="Prompt Design",
        lane="manual",
        status="accepted",
        claim="Rules in prose are probabilistic.",
        mechanism="Attention and salience make prompt compliance probabilistic.",
        commercial_design_law="Business-critical rules should be structural.",
        ender_implication="Gate high-stakes actions with deterministic state.",
        experiment_30_day="Replay prompt-only versus tool-gated conversations.",
        evidence=[Evidence(quote="Prompt instructions are attention architecture.")],
        confidence="high",
        novelty="high",
        decision_impact="high",
        created_at=datetime.now(UTC),
    )
    assert insight.status == "accepted"
