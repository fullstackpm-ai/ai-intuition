from pathlib import Path

from app.evals.assertions import assert_quality_bar
from app.evals.golden import run_prompt_design_golden


def test_prompt_design_golden_produces_expected_design_law() -> None:
    insights = run_prompt_design_golden(Path("data/golden/prompt-design-principles.md"))
    accepted = [insight for insight in insights if insight.status == "accepted"]
    assert accepted
    assert_quality_bar(accepted[0])
    assert "tools, code, schemas, validators, permissions, and workflow state" in (
        accepted[0].design_law or ""
    )
    assert "probabilistic interpreter" in accepted[0].intuition_update
