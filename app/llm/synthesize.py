from __future__ import annotations

from pathlib import Path

from app.models import ExtractedInsight, WeeklyBrief
from app.store.files import write_markdown
from app.time import now_utc


def build_weekly_brief(week: str, insights: list[ExtractedInsight], output_dir: Path) -> tuple[WeeklyBrief, Path]:
    accepted = [insight for insight in insights if insight.status == "accepted"]
    review = [insight for insight in insights if insight.status == "needs_human_review"]
    thesis = "Durable AI intuition comes from mechanisms, boundaries, and structural controls rather than summaries."
    brief = WeeklyBrief(
        week=week,
        generated_at=now_utc(),
        one_line_thesis=thesis if accepted else "No accepted belief updates this week.",
        belief_updates=[insight.intuition_update or insight.claim for insight in accepted[:3]],
        new_or_updated_mental_models=[insight.mental_model for insight in accepted if insight.mental_model],
        new_or_updated_design_laws=[insight.design_law for insight in accepted if insight.design_law],
        new_failure_modes=[insight.failure_mode for insight in accepted if insight.failure_mode],
        new_eval_patterns=[insight.eval_pattern for insight in accepted if insight.eval_pattern],
        strategy_updates=[insight.strategy_implication for insight in accepted if insight.strategy_implication],
        learning_experiments=[insight.learning_experiment for insight in accepted if insight.learning_experiment],
        intuition_drills=[insight.intuition_drill for insight in accepted if insight.intuition_drill],
        ignored_noise=[insight.discard_reason for insight in insights if insight.status == "rejected" and insight.discard_reason],
        source_rollup=[f"{insight.source_id}: {insight.source_title}" for insight in accepted],
        human_review_flags=[insight.claim for insight in review],
    )
    body = render_weekly_brief_markdown(brief)
    destination = output_dir / f"{week}.md"
    write_markdown(
        destination,
        {
            "week": week,
            "generated_at": brief.generated_at.isoformat(),
            "accepted_insights": len(accepted),
            "human_review_flags": len(review),
        },
        body,
    )
    return brief, destination


def render_weekly_brief_markdown(brief: WeeklyBrief) -> str:
    lines = [
        f"# AI Intuition Brief - {brief.week}",
        "",
        "## One-line thesis",
        "",
        brief.one_line_thesis,
        "",
        "## 3 belief updates",
        "",
    ]
    lines.extend(_numbered(brief.belief_updates))
    lines.extend(["", "## New or updated mental models", ""])
    lines.extend(_bullets(brief.new_or_updated_mental_models))
    lines.extend(["", "## New or updated agent design laws", ""])
    lines.extend(_bullets(brief.new_or_updated_design_laws))
    lines.extend(["", "## New failure modes to track", ""])
    lines.extend(_bullets(brief.new_failure_modes))
    lines.extend(["", "## New eval patterns", ""])
    lines.extend(_bullets(brief.new_eval_patterns))
    lines.extend(["", "## Strategy / value-capture updates", ""])
    lines.extend(_bullets(brief.strategy_updates))
    lines.extend(["", "## Learning experiments / intuition drills", ""])
    lines.extend(_numbered([*brief.learning_experiments, *brief.intuition_drills]))
    lines.extend(["", "## Ignored noise", ""])
    lines.extend(_bullets(brief.ignored_noise or ["No rejected noise recorded."]))
    lines.extend(["", "## Human review flags", ""])
    lines.extend(_bullets(brief.human_review_flags or ["None."]))
    return "\n".join(lines).strip() + "\n"


def _bullets(values: list[str]) -> list[str]:
    return [f"- {value}" for value in values] or ["- None."]


def _numbered(values: list[str]) -> list[str]:
    return [f"{index}. {value}" for index, value in enumerate(values, start=1)] or ["None."]
