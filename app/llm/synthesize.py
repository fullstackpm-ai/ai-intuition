from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from app.models import ExtractedInsight, WeeklyBrief
from app.store.files import write_markdown
from app.time import now_utc


ENDER_AREAS = ["Leasing", "Maintenance", "Accounting", "Collections", "Support", "Platform / architecture"]


def build_weekly_brief(week: str, insights: list[ExtractedInsight], output_dir: Path) -> tuple[WeeklyBrief, Path]:
    accepted = [insight for insight in insights if insight.status == "accepted"]
    review = [insight for insight in insights if insight.status == "needs_human_review"]
    thesis = "Commercial agent reliability comes from structural constraints, not prose-only instructions."
    implications: dict[str, list[str]] = defaultdict(list)
    for insight in accepted:
        implication = insight.ender_implication or ""
        implications["Platform / architecture"].append(implication)
        if "tour" in implication.lower():
            implications["Leasing"].append(implication)
        if any(term in implication.lower() for term in ["fee", "ledger", "deposit", "credit", "write-off"]):
            implications["Accounting"].append(implication)
        if "collections" in implication.lower():
            implications["Collections"].append(implication)
    normalized_implications = {area: implications.get(area, []) for area in ENDER_AREAS}
    brief = WeeklyBrief(
        week=week,
        generated_at=now_utc(),
        one_line_thesis=thesis if accepted else "No accepted belief updates this week.",
        belief_updates=[insight.claim for insight in accepted[:3]],
        new_or_updated_design_laws=[insight.commercial_design_law for insight in accepted if insight.commercial_design_law],
        new_failure_modes=[insight.failure_mode for insight in accepted if insight.failure_mode],
        ender_implications=normalized_implications,
        experiments=[insight.experiment_30_day for insight in accepted if insight.experiment_30_day],
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
        f"# AI Operating Intelligence - {brief.week}",
        "",
        "## One-line thesis",
        "",
        brief.one_line_thesis,
        "",
        "## 3 belief updates",
        "",
    ]
    lines.extend(_numbered(brief.belief_updates))
    lines.extend(["", "## New or updated agent design laws", ""])
    lines.extend(_bullets(brief.new_or_updated_design_laws))
    lines.extend(["", "## New failure modes to track", ""])
    lines.extend(_bullets(brief.new_failure_modes))
    lines.extend(["", "## Ender implications", ""])
    for area, values in brief.ender_implications.items():
        lines.extend([f"### {area}", ""])
        lines.extend(_bullets(values or ["No accepted implication this week."]))
        lines.append("")
    lines.extend(["## Experiments to run in 30 days", ""])
    lines.extend(_numbered(brief.experiments))
    lines.extend(["", "## Ignored noise", ""])
    lines.extend(_bullets(brief.ignored_noise or ["No rejected noise recorded."]))
    lines.extend(["", "## Human review flags", ""])
    lines.extend(_bullets(brief.human_review_flags or ["None."]))
    return "\n".join(lines).strip() + "\n"


def _bullets(values: list[str]) -> list[str]:
    return [f"- {value}" for value in values]


def _numbered(values: list[str]) -> list[str]:
    return [f"{index}. {value}" for index, value in enumerate(values, start=1)] or ["None."]
