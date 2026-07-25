from __future__ import annotations

from app.models import ExtractedInsight


def assert_quality_bar(insight: ExtractedInsight) -> None:
    assert insight.mechanism
    assert insight.intuition_update
    assert insight.evidence
    assert insight.mental_model or insight.design_law or insight.failure_mode or insight.eval_pattern or insight.strategy_implication
