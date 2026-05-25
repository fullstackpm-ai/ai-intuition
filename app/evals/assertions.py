from __future__ import annotations

from app.models import ExtractedInsight


def assert_quality_bar(insight: ExtractedInsight) -> None:
    assert insight.mechanism
    assert insight.ender_implication
    assert insight.experiment_30_day
    assert insight.evidence
    assert insight.commercial_design_law or insight.failure_mode
