from __future__ import annotations

import json
from datetime import UTC, datetime

from app import cli
from app.llm.extract import import_insights_from_json, load_insight_artifacts
from app.llm.synthesize import build_weekly_brief, filter_insights_for_published_week
from app.models import Evidence, ExtractedInsight, NormalizedItem, SourceReference
from app.observability import RunContext
from app.store.db import StateStore
from app.store.files import read_markdown, write_json, write_markdown


def _insight(
    insight_id: str,
    *,
    item_id: str = "item",
    source_id: str = "anthropic_research",
    source_name: str | None = "Anthropic Research",
    source_type: str | None = "lab_research",
    source_title: str = "Project Pilot",
    source_url: str | None = "https://example.com/project-pilot",
    published_at: datetime | None = datetime(2026, 7, 24, tzinfo=UTC),
    source_references: list[SourceReference] | None = None,
    extraction_method: str = "codex_packet",
) -> ExtractedInsight:
    return ExtractedInsight(
        id=insight_id,
        item_id=item_id,
        source_id=source_id,
        source_name=source_name,
        source_type=source_type,
        source_title=source_title,
        source_url=source_url,
        raw_artifact_id=f"{item_id}_raw",
        raw_path=f"data/raw/lab-posts/{item_id}.html",
        normalized_path=f"data/normalized/{item_id}.md",
        published_at=published_at,
        lane="reliability_failures",
        status="accepted",
        claim="Reliability belongs to the harness.",
        mechanism="The system controls tools, context, observations, and termination.",
        intuition_update="Ask which layer owns each reliability property.",
        mental_model="Agent reliability is a system property.",
        design_law="The harness is the reliability layer.",
        evidence=[Evidence(quote="Harness evidence.", location="section 1")],
        confidence="high",
        novelty="high",
        mental_model_impact="high",
        extraction_method=extraction_method,
        extraction_model="codex",
        source_references=source_references or [],
        created_at=datetime(2026, 7, 25, tzinfo=UTC),
    )


def test_weekly_brief_renders_single_source_marker_sources_section_and_frontmatter(tmp_path) -> None:
    _, path = build_weekly_brief("2026-W30", [_insight("i1")], tmp_path)
    metadata, body = read_markdown(path)

    assert "Ask which layer owns each reliability property. [S1]" in body
    assert "## Sources" in body
    assert '- [S1] Anthropic Research - "Project Pilot" (lab_research, 2026-07-24)' in body
    assert "  https://example.com/project-pilot" in body
    assert metadata["source_attribution_summary"]["unique_source_artifacts"] == 1
    assert metadata["source_references"][0]["ref_id"] == "S1"
    assert metadata["source_references"][0]["insight_ids"] == ["i1"]


def test_weekly_brief_dedupes_repeated_source_artifacts(tmp_path) -> None:
    first = _insight("i1", item_id="same", source_title="Same Article")
    second = _insight("i2", item_id="same", source_title="Same Article")

    _, path = build_weekly_brief("2026-W30", [first, second], tmp_path)
    metadata, body = read_markdown(path)

    assert body.count("[S1]") >= 3
    assert body.count('- [S1] Anthropic Research - "Same Article"') == 1
    assert metadata["source_attribution_summary"]["unique_source_artifacts"] == 1
    assert metadata["source_references"][0]["insight_ids"] == ["i1", "i2"]


def test_weekly_brief_renders_multi_source_markers_once_per_source(tmp_path) -> None:
    source_references = [
        SourceReference(
            source_id="anthropic_research",
            source_name="Anthropic Research",
            source_type="lab_research",
            item_id="pilot",
            title="Project Pilot",
            url="https://example.com/pilot",
            published_at=datetime(2026, 7, 24, tzinfo=UTC),
        ),
        SourceReference(
            source_id="lenny_podcast",
            source_name="Lenny's Podcast",
            source_type="podcast",
            item_id="netflix",
            title="Systems Thinkers",
            url="https://example.com/netflix",
            published_at=datetime(2026, 7, 19, tzinfo=UTC),
        ),
    ]
    insight = _insight("i1", item_id="synthesis", source_references=source_references)

    _, path = build_weekly_brief("2026-W30", [insight], tmp_path)
    metadata, body = read_markdown(path)

    assert "Ask which layer owns each reliability property. [S1, S2]" in body
    assert body.count('- [S1] Anthropic Research - "Project Pilot"') == 1
    assert body.count('- [S2] Lenny\'s Podcast - "Systems Thinkers"') == 1
    assert metadata["source_attribution_summary"]["unique_source_artifacts"] == 2


def test_weekly_brief_handles_missing_metadata_without_inventing_it(tmp_path) -> None:
    insight = _insight(
        "i1",
        source_name=None,
        source_type=None,
        source_title="Prompt Design Principles",
        source_url=None,
        published_at=None,
        extraction_method="legacy",
    )

    _, path = build_weekly_brief("2026-W30", [insight], tmp_path)
    metadata, body = read_markdown(path)

    assert '- [S1] anthropic_research - "Prompt Design Principles" (type unknown, date unknown)' in body
    assert "https://example.com" not in body
    assert metadata["source_attribution_summary"]["missing_url"] == 1
    assert metadata["source_attribution_summary"]["missing_date"] == 1
    assert "1 source reference(s) missing URL." in metadata["source_attribution_warnings"]


def test_imported_extraction_infers_source_attribution_from_normalized_item(tmp_path) -> None:
    item = NormalizedItem(
        id="codex_loop",
        raw_artifact_id="raw_codex_loop",
        source_id="openai_research",
        source_name="OpenAI Research",
        source_type="lab_research",
        lane="product_patterns",
        title="Unrolling the Codex agent loop",
        url="https://openai.com/index/unrolling-the-codex-agent-loop/",
        published_at=datetime(2026, 1, 23, tzinfo=UTC),
        raw_path="data/raw/lab-posts/codex_loop.html",
        normalized_path="data/normalized/codex_loop.md",
        text="Agents are managed execution loops.",
        word_count=5,
    )
    path = tmp_path / "codex_loop.json"
    write_json(
        path,
        [
            {
                "status": "accepted",
                "claim": "Agents are managed execution loops.",
                "mechanism": "The harness repeats model calls and tool calls.",
                "intuition_update": "Think of agents as runtimes.",
                "mental_model": "Agent = model plus harness.",
                "evidence": [{"quote": "Loop evidence.", "location": "agent loop section"}],
                "confidence": "high",
                "novelty": "high",
                "mental_model_impact": "high",
            }
        ],
    )

    insight = import_insights_from_json(item, path)[0]

    assert insight.source_name == "OpenAI Research"
    assert insight.source_type == "lab_research"
    assert insight.raw_artifact_id == "raw_codex_loop"
    assert insight.normalized_path == "data/normalized/codex_loop.md"
    assert insight.published_at == datetime(2026, 1, 23, tzinfo=UTC)


def test_legacy_extraction_artifact_recovers_published_date_from_normalized_item(tmp_path) -> None:
    data_dir = tmp_path / "data"
    write_markdown(
        data_dir / "normalized" / "dwarkesh_may.md",
        {
            "id": "dwarkesh_may",
            "raw_artifact_id": "raw_dwarkesh_may",
            "source_id": "dwarkesh_podcast",
            "source_name": "Dwarkesh Podcast",
            "source_type": "podcast_transcript",
            "lane": "frontier_priors",
            "title": "Eric Jang - Building AlphaGo from scratch",
            "url": "https://www.dwarkesh.com/p/eric-jang",
            "published_at": "2026-05-15T16:04:58+00:00",
            "raw_path": "data/raw/podcasts/dwarkesh_may.md",
        },
        "# Transcript\n",
    )
    write_json(
        data_dir / "extracted" / "dwarkesh_may.json",
        [
            {
                "id": "dwarkesh_may_insight_0",
                "item_id": "dwarkesh_may",
                "source_id": "dwarkesh_podcast",
                "source_title": "Eric Jang - Building AlphaGo from scratch",
                "source_url": "https://www.dwarkesh.com/p/eric-jang",
                "lane": "frontier_priors",
                "status": "accepted",
                "claim": "Rebuilding systems reveals hidden constraints.",
                "mechanism": "Implementation exposes choices hidden by paper-level summaries.",
                "intuition_update": "Use rebuilds as a way to internalize AI systems.",
                "mental_model": "Replication is embodied understanding.",
                "evidence": [{"quote": "AlphaGo evidence.", "location": "transcript"}],
                "confidence": "high",
                "novelty": "high",
                "mental_model_impact": "high",
                "created_at": "2026-07-24T00:00:00-07:00",
            }
        ],
    )

    insights = load_insight_artifacts(data_dir)

    assert insights[0].published_at == datetime(2026, 5, 15, 16, 4, 58, tzinfo=UTC)
    assert insights[0].source_name == "Dwarkesh Podcast"
    assert insights[0].source_type == "podcast_transcript"


def test_week_filter_uses_published_at_not_extraction_created_at() -> None:
    may_source_processed_in_week_30 = _insight(
        "dwarkesh_may",
        item_id="dwarkesh_may",
        source_id="dwarkesh_podcast",
        source_name="Dwarkesh Podcast",
        source_type="podcast_transcript",
        source_title="Eric Jang - Building AlphaGo from scratch",
        source_url="https://www.dwarkesh.com/p/eric-jang",
        published_at=datetime(2026, 5, 15, tzinfo=UTC),
    )
    july_source = _insight(
        "anthropic_july",
        item_id="anthropic_july",
        published_at=datetime(2026, 7, 24, tzinfo=UTC),
    )

    selected = filter_insights_for_published_week([may_source_processed_in_week_30, july_source], "2026-W30")

    assert [insight.id for insight in selected] == ["anthropic_july"]


def test_brief_stage_loads_extraction_artifacts_and_filters_by_published_week(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    store = StateStore(tmp_path / "state.sqlite3")
    monkeypatch.setattr(cli, "DATA_DIR", data_dir)
    try:
        for item_id, title, published_at in [
            ("dwarkesh_may", "Eric Jang - Building AlphaGo from scratch", "2026-05-15T16:04:58+00:00"),
            ("anthropic_july", "Project Pilot", "2026-07-24T00:00:00+00:00"),
        ]:
            write_markdown(
                data_dir / "normalized" / f"{item_id}.md",
                {
                    "id": item_id,
                    "raw_artifact_id": f"raw_{item_id}",
                    "source_id": "dwarkesh_podcast" if item_id == "dwarkesh_may" else "anthropic_research",
                    "source_name": "Dwarkesh Podcast" if item_id == "dwarkesh_may" else "Anthropic Research",
                    "source_type": "podcast_transcript" if item_id == "dwarkesh_may" else "lab_research",
                    "lane": "frontier_priors",
                    "title": title,
                    "url": f"https://example.com/{item_id}",
                    "published_at": published_at,
                    "raw_path": f"data/raw/{item_id}.md",
                },
                "# Source\n",
            )
            write_json(
                data_dir / "extracted" / f"{item_id}.json",
                [
                    {
                        "id": f"{item_id}_insight_0",
                        "item_id": item_id,
                        "source_id": "dwarkesh_podcast" if item_id == "dwarkesh_may" else "anthropic_research",
                        "source_title": title,
                        "source_url": f"https://example.com/{item_id}",
                        "lane": "frontier_priors",
                        "status": "accepted",
                        "claim": f"{title} has a durable lesson.",
                        "mechanism": "Mechanism.",
                        "intuition_update": f"Internalize {title}.",
                        "mental_model": f"{title} model.",
                        "evidence": [{"quote": "Evidence.", "location": "source"}],
                        "confidence": "high",
                        "novelty": "high",
                        "mental_model_impact": "high",
                        "extraction_method": "codex_packet",
                        "created_at": "2026-07-24T00:00:00-07:00",
                    }
                ],
            )

        path = cli._run_brief(store, week="2026-W30")
    finally:
        store.close()

    metadata, body = read_markdown(path)
    assert metadata["accepted_insights"] == 1
    assert metadata["source_attribution_summary"]["unique_source_artifacts"] == 1
    assert metadata["source_references"][0]["title"] == "Project Pilot"
    assert "Project Pilot" in body
    assert "Eric Jang" not in body


def test_brief_stage_records_source_attribution_observability(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    store = StateStore(tmp_path / "state.sqlite3")
    context = RunContext("run-weekly", data_dir, options={"extraction_mode": "mock"}, run_id="brief-run")
    context.start()
    monkeypatch.setattr(cli, "DATA_DIR", data_dir)
    try:
        store.upsert_insights([_insight("i1")])
        cli._run_brief(store, week="2026-W30", run_context=context)
    finally:
        store.close()

    events = [json.loads(line) for line in (data_dir / "runs" / "brief-run" / "events.jsonl").read_text().splitlines()]
    attribution_events = [event for event in events if event["event_type"] == "brief_attribution_summarized"]

    assert len(attribution_events) == 1
    assert attribution_events[0]["metadata"]["source_attribution_summary"]["unique_source_artifacts"] == 1
