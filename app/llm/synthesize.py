from __future__ import annotations

from collections import Counter
from pathlib import Path

from app.models import ExtractedInsight, SourceReference, WeeklyBrief
from app.store.files import write_markdown
from app.time import now_utc


def build_weekly_brief(week: str, insights: list[ExtractedInsight], output_dir: Path) -> tuple[WeeklyBrief, Path]:
    accepted = [insight for insight in insights if insight.status == "accepted"]
    review = [insight for insight in insights if insight.status == "needs_human_review"]
    extraction_provenance = dict(Counter(insight.extraction_method for insight in accepted))
    source_references, source_markers = build_source_references(accepted)
    attribution_summary, attribution_warnings = summarize_source_attribution(accepted, source_references)
    risky_methods = sorted(method for method in extraction_provenance if method in {"mock", "legacy"})
    extraction_warning = None
    if risky_methods:
        extraction_warning = f"Accepted insights include {', '.join(risky_methods)} extraction provenance; treat this brief as not fully source-grounded."
    thesis = "Durable AI intuition comes from mechanisms, boundaries, and structural controls rather than summaries."
    brief = WeeklyBrief(
        week=week,
        generated_at=now_utc(),
        one_line_thesis=thesis if accepted else "No accepted belief updates this week.",
        belief_updates=[_with_source_marker(insight.intuition_update or insight.claim, insight, source_markers) for insight in accepted[:3]],
        new_or_updated_mental_models=[
            _with_source_marker(insight.mental_model, insight, source_markers) for insight in accepted if insight.mental_model
        ],
        new_or_updated_design_laws=[
            _with_source_marker(insight.design_law, insight, source_markers) for insight in accepted if insight.design_law
        ],
        new_failure_modes=[
            _with_source_marker(insight.failure_mode, insight, source_markers) for insight in accepted if insight.failure_mode
        ],
        new_eval_patterns=[
            _with_source_marker(insight.eval_pattern, insight, source_markers) for insight in accepted if insight.eval_pattern
        ],
        strategy_updates=[
            _with_source_marker(insight.strategy_implication, insight, source_markers)
            for insight in accepted
            if insight.strategy_implication
        ],
        learning_experiments=[
            _with_source_marker(insight.learning_experiment, insight, source_markers)
            for insight in accepted
            if insight.learning_experiment
        ],
        intuition_drills=[
            _with_source_marker(insight.intuition_drill, insight, source_markers)
            for insight in accepted
            if insight.intuition_drill
        ],
        ignored_noise=[insight.discard_reason for insight in insights if insight.status == "rejected" and insight.discard_reason],
        source_rollup=[_format_source_reference(reference) for reference in source_references],
        human_review_flags=[insight.claim for insight in review],
        extraction_provenance=extraction_provenance,
        extraction_warning=extraction_warning,
        source_references=source_references,
        source_attribution_summary=attribution_summary,
        source_attribution_warnings=attribution_warnings,
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
            "extraction_provenance": extraction_provenance,
            "extraction_warning": extraction_warning,
            "source_references": [reference.model_dump(mode="json") for reference in source_references],
            "source_attribution_summary": attribution_summary,
            "source_attribution_warnings": attribution_warnings,
        },
        body,
    )
    return brief, destination


def build_source_references(insights: list[ExtractedInsight]) -> tuple[list[SourceReference], dict[str, list[str]]]:
    references_by_key: dict[tuple[str, str, str | None], SourceReference] = {}
    markers_by_insight: dict[str, list[str]] = {}

    for insight in insights:
        markers = []
        for source in _source_candidates(insight):
            key = _source_key(source)
            reference = references_by_key.get(key)
            if reference is None:
                reference = source.model_copy(update={"ref_id": f"S{len(references_by_key) + 1}"})
                references_by_key[key] = reference
            if insight.extraction_method not in reference.extraction_methods:
                reference.extraction_methods.append(insight.extraction_method)
            if insight.id not in reference.insight_ids:
                reference.insight_ids.append(insight.id)
            if reference.ref_id:
                markers.append(reference.ref_id)
        markers_by_insight[insight.id] = markers

    return list(references_by_key.values()), markers_by_insight


def summarize_source_attribution(
    insights: list[ExtractedInsight],
    source_references: list[SourceReference],
) -> tuple[dict[str, int], list[str]]:
    summary = {
        "accepted_insights": len(insights),
        "unique_source_artifacts": len(source_references),
        "missing_url": sum(1 for reference in source_references if not reference.url),
        "missing_date": sum(1 for reference in source_references if not reference.published_at),
        "missing_source_name": sum(1 for reference in source_references if not reference.source_name),
        "missing_source_type": sum(1 for reference in source_references if not reference.source_type),
    }
    warnings = []
    for field, label in [
        ("missing_url", "URL"),
        ("missing_date", "publish date"),
        ("missing_source_name", "source name"),
        ("missing_source_type", "source type"),
    ]:
        count = summary[field]
        if count:
            warnings.append(f"{count} source reference(s) missing {label}.")
    return summary, warnings


def _source_candidates(insight: ExtractedInsight) -> list[SourceReference]:
    if insight.source_references:
        return [
            reference.model_copy(
                update={
                    "extraction_methods": list(reference.extraction_methods),
                    "insight_ids": list(reference.insight_ids),
                }
            )
            for reference in insight.source_references
        ]
    return [
        SourceReference(
            source_id=insight.source_id,
            source_name=insight.source_name,
            source_type=insight.source_type,
            item_id=insight.item_id,
            raw_artifact_id=insight.raw_artifact_id,
            title=insight.source_title,
            url=insight.source_url,
            published_at=insight.published_at,
            raw_path=insight.raw_path,
            normalized_path=insight.normalized_path,
        )
    ]


def _source_key(reference: SourceReference) -> tuple[str, str, str | None]:
    return (reference.source_id, reference.item_id, reference.url)


def _with_source_marker(value: str | None, insight: ExtractedInsight, markers_by_insight: dict[str, list[str]]) -> str:
    text = value or ""
    markers = markers_by_insight.get(insight.id, [])
    if not markers:
        return text
    return f"{text} [{', '.join(markers)}]"


def render_weekly_brief_markdown(brief: WeeklyBrief) -> str:
    lines = [
        f"# AI Intuition Brief - {brief.week}",
        "",
        "## One-line thesis",
        "",
        brief.one_line_thesis,
        "",
        "## Extraction provenance",
        "",
    ]
    lines.extend(_bullets([f"{method}: {count}" for method, count in sorted(brief.extraction_provenance.items())] or ["No accepted insights."]))
    if brief.extraction_warning:
        lines.extend(["", f"Warning: {brief.extraction_warning}"])
    lines.extend([
        "",
        "## 3 belief updates",
        "",
    ])
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
    lines.extend(["", "## Sources", ""])
    lines.extend(_source_reference_lines(brief.source_references))
    return "\n".join(lines).strip() + "\n"


def _source_reference_lines(references: list[SourceReference]) -> list[str]:
    if not references:
        return ["- No accepted source references."]
    lines = []
    for reference in references:
        lines.append(f"- {_format_source_reference(reference)}")
        if reference.url:
            lines.append(f"  {reference.url}")
    return lines


def _format_source_reference(reference: SourceReference) -> str:
    ref_id = reference.ref_id or "S?"
    source_name = reference.source_name or reference.source_id or "unknown source"
    source_type = reference.source_type or "type unknown"
    published_at = reference.published_at.date().isoformat() if reference.published_at else "date unknown"
    return f"[{ref_id}] {source_name} - \"{reference.title}\" ({source_type}, {published_at})"


def _bullets(values: list[str]) -> list[str]:
    return [f"- {value}" for value in values] or ["- None."]


def _numbered(values: list[str]) -> list[str]:
    return [f"{index}. {value}" for index, value in enumerate(values, start=1)] or ["None."]
