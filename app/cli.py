from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer

from app.config import DATA_DIR, DB_PATH, enabled_sources
from app.ingest.discovery import DateWindow, discover_source
from app.ingest.manual import ingest_manual_directory, ingest_manual_file
from app.ingest.rss import ingest_podcast_episode_pages, ingest_rss_or_html_source
from app.ingest.transcript import UseTranscribeClient, write_transcript_raw_artifact
from app.llm.belief_update import update_beliefs
from app.llm.edit import edit_insights
from app.llm.extract import extract_insights
from app.llm.prompts import EXTRACTION_PROMPT
from app.llm.synthesize import build_weekly_brief
from app.logging import console
from app.models import Source
from app.normalize.normalize import normalize_raw_artifact
from app.store.db import StateStore
from app.store.files import ensure_data_dirs, read_json, write_json
from app.time import current_week, now_local, parse_since

app = typer.Typer(help="AI Intuition Compiler CLI")


def _manual_source() -> Source:
    matches = [source for source in enabled_sources("manual") if source.type == "manual"]
    if matches:
        return matches[0]
    return Source(id="manual", name="Manual Inputs", lane="manual", type="manual", path="data/raw/manual")


def _store() -> StateStore:
    ensure_data_dirs(Path.cwd())
    store = StateStore(DB_PATH)
    store.upsert_sources(enabled_sources())
    return store


@app.command()
def ingest(
    since: Annotated[str, typer.Option(help="Only ingest discovered items newer than this window when publish dates are available.")] = "7d",
    source: Annotated[str | None, typer.Option(help="Source id to ingest.")] = None,
    manual: Annotated[Path | None, typer.Option(help="Manual markdown source to ingest.")] = None,
) -> None:
    """Save raw artifacts and update SQLite without calling the LLM."""
    store = _store()
    created = 0
    try:
        artifacts = []
        window = DateWindow(start=parse_since(since), end=now_local())
        if manual:
            artifacts.append(ingest_manual_file(manual, _manual_source(), DATA_DIR / "raw"))
        else:
            for configured in enabled_sources(source):
                try:
                    adapter = configured.adapter or configured.type
                    if adapter == "manual" or configured.type == "manual":
                        artifacts.extend(ingest_manual_directory(configured, Path.cwd()))
                    elif adapter in {"rss_or_html", "html_index"}:
                        if configured.rss_url_env and os.getenv(configured.rss_url_env):
                            configured.urls = [os.environ[configured.rss_url_env], *configured.urls]
                        artifacts.extend(ingest_rss_or_html_source(configured, DATA_DIR / "raw", window=window))
                    elif adapter == "podcast_episode_page_or_youtube":
                        artifacts.extend(ingest_podcast_episode_pages(configured, DATA_DIR / "raw", window=window))
                except Exception as exc:  # Network sources should not block manual pipeline progress.
                    console.print(f"[yellow]Skipped {configured.id}: {exc}[/yellow]")
        for artifact in artifacts:
            if store.upsert_raw(artifact):
                created += 1
        store.log_run("ingest", {"since": since, "source": source, "manual": str(manual) if manual else None, "created": created})
    finally:
        store.close()
    console.print(f"Ingested {created} new raw artifact(s).")


@app.command()
def discover(
    since: Annotated[str, typer.Option(help="Only show items newer than this window when publish dates are available.")] = "7d",
    source: Annotated[str | None, typer.Option(help="Source id to discover.")] = None,
    limit: Annotated[int, typer.Option(help="Maximum items per source.")] = 10,
) -> None:
    """Discover candidate articles or podcast/video URLs without ingesting them."""
    window = DateWindow(start=parse_since(since), end=now_local())
    rows = []
    for configured in enabled_sources(source):
        adapter = configured.adapter or configured.type
        if adapter in {"manual"} or configured.type == "manual":
            continue
        try:
            if configured.rss_url_env and os.getenv(configured.rss_url_env):
                configured.urls = [os.environ[configured.rss_url_env], *configured.urls]
            for item in discover_source(configured, window, limit=limit):
                rows.append(
                    {
                        "source": configured.id,
                        "type": item.item_type,
                        "published_at": item.published_at.isoformat() if item.published_at else None,
                        "title": item.title,
                        "url": item.url,
                    }
                )
        except Exception as exc:
            console.print(f"[yellow]Skipped {configured.id}: {exc}[/yellow]")
    console.print_json(data=rows)


@app.command()
def normalize(
    since: Annotated[str, typer.Option(help="Currently accepted for command compatibility.")] = "7d",
    item: Annotated[str | None, typer.Option(help="Raw artifact id to normalize.")] = None,
) -> None:
    """Convert raw artifacts into clean markdown normalized items."""
    store = _store()
    count = 0
    try:
        for artifact in store.list_raw(item):
            normalized = normalize_raw_artifact(artifact, DATA_DIR / "normalized")
            store.upsert_normalized(normalized)
            count += 1
        store.log_run("normalize", {"since": since, "item": item, "count": count})
    finally:
        store.close()
    console.print(f"Normalized {count} item(s).")


@app.command()
def extract(
    since: Annotated[str, typer.Option(help="Currently accepted for command compatibility.")] = "7d",
    item: Annotated[str | None, typer.Option(help="Normalized item id to extract.")] = None,
    mock_llm: Annotated[bool, typer.Option(help="Use deterministic mocked LLM support.")] = True,
) -> None:
    """Run extraction prompt plumbing over normalized items."""
    store = _store()
    count = 0
    try:
        for normalized in store.list_normalized(item):
            insights = extract_insights(normalized)
            accepted_path = DATA_DIR / "extracted" / f"{normalized.id}.json"
            rejected_path = DATA_DIR / "rejected" / f"{normalized.id}.json"
            write_json(accepted_path, [insight.model_dump(mode="json") for insight in insights if insight.status != "rejected"])
            write_json(rejected_path, [insight.model_dump(mode="json") for insight in insights if insight.status == "rejected"])
            store.upsert_insights(insights)
            count += len(insights)
        store.log_run("extract", {"since": since, "item": item, "mock_llm": mock_llm, "count": count})
    finally:
        store.close()
    console.print(f"Extracted {count} insight candidate(s).")


@app.command("extract-packet")
def extract_packet(
    item: Annotated[str | None, typer.Option(help="Normalized item id to packet. Omit to packet all normalized items.")] = None,
) -> None:
    """Write Codex-ready extraction packets for normalized items."""
    store = _store()
    count = 0
    try:
        for normalized in store.list_normalized(item):
            schema_hint = """
Return a JSON list of ExtractedInsight-like objects using these fields:
- claim
- mechanism
- intuition_update
- mental_model
- design_law
- failure_mode
- eval_pattern
- boundary_conditions
- counterargument
- strategy_implication
- learning_experiment
- intuition_drill
- open_question
- evidence: [{quote, location, note}]
- confidence: low | medium | high
- novelty: low | medium | high
- mental_model_impact: low | medium | high
- discard_reason for rejected summaries
""".strip()
            body = "\n\n".join(
                [
                    f"# Extraction Packet: {normalized.title}",
                    "## Output paths",
                    f"- Accepted/candidate insights: `data/extracted/{normalized.id}.json`",
                    f"- Rejected insights: `data/rejected/{normalized.id}.json`",
                    "## Source metadata",
                    f"- item_id: `{normalized.id}`",
                    f"- source_id: `{normalized.source_id}`",
                    f"- lane: `{normalized.lane}`",
                    f"- title: `{normalized.title}`",
                    f"- url: `{normalized.url}`",
                    f"- published_at: `{normalized.published_at}`",
                    "## Schema guidance",
                    schema_hint,
                    "## Extraction prompt",
                    EXTRACTION_PROMPT.format(lane=normalized.lane, title=normalized.title, text=normalized.text),
                ]
            )
            path = DATA_DIR / "extraction-packets" / f"{normalized.id}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body + "\n")
            count += 1
        store.log_run("extract-packet", {"item": item, "count": count})
    finally:
        store.close()
    console.print(f"Wrote {count} extraction packet(s).")


@app.command()
def edit(since: Annotated[str, typer.Option(help="Currently accepted for command compatibility.")] = "7d") -> None:
    """Apply adversarial editor scoring rules to candidate insights."""
    store = _store()
    try:
        insights = store.list_insights()
        edited = edit_insights(insights)
        by_item: dict[str, list[object]] = {}
        rejected_by_item: dict[str, list[object]] = {}
        for insight in edited:
            target = rejected_by_item if insight.status == "rejected" else by_item
            target.setdefault(insight.item_id, []).append(insight.model_dump(mode="json"))
        for item_id, payload in by_item.items():
            write_json(DATA_DIR / "extracted" / f"{item_id}.json", payload)
        for item_id, payload in rejected_by_item.items():
            write_json(DATA_DIR / "rejected" / f"{item_id}.json", payload)
        store.upsert_insights(edited)
        store.log_run("edit", {"since": since, "count": len(edited)})
    finally:
        store.close()
    console.print(f"Edited {len(insights)} insight(s).")


@app.command()
def brief(
    week: Annotated[str | None, typer.Option(help="ISO week, e.g. 2026-W22.")] = None,
    current_week_flag: Annotated[bool, typer.Option("--current-week", help="Use the current ISO week.")] = False,
) -> None:
    """Generate a markdown weekly brief from accepted extracted JSON."""
    target_week = current_week() if current_week_flag or not week else week
    store = _store()
    try:
        insights = store.list_insights()
        _, path = build_weekly_brief(target_week, insights, DATA_DIR / "briefs")
        store.log_run("brief", {"week": target_week, "path": str(path)})
    finally:
        store.close()
    console.print(f"Wrote {path}")


@app.command("belief-update")
def belief_update(
    week: Annotated[str | None, typer.Option(help="ISO week, e.g. 2026-W22.")] = None,
    current_week_flag: Annotated[bool, typer.Option("--current-week", help="Use the current ISO week.")] = False,
) -> None:
    """Append accepted durable updates to belief files."""
    target_week = current_week() if current_week_flag or not week else week
    store = _store()
    try:
        touched = update_beliefs(target_week, store.list_insights(), DATA_DIR / "beliefs")
        store.log_run("belief-update", {"week": target_week, "touched": [str(path) for path in touched]})
    finally:
        store.close()
    console.print(f"Updated {len(touched)} belief file(s).")


@app.command()
def send(week: Annotated[str | None, typer.Option(help="ISO week, e.g. 2026-W22.")] = None) -> None:
    """Email sending is intentionally deferred to Milestone 2."""
    raise typer.BadParameter("Email sending is Phase 2 and is not implemented in Milestone 1.")


@app.command()
def transcribe(
    url: Annotated[str, typer.Option("--url", help="YouTube URL, or legacy cached Spotify episode URL, to fetch via useTranscribe.")],
    source: Annotated[str, typer.Option("--source", help="Configured podcast source id.")],
) -> None:
    """Transcribe a known YouTube URL or fetch a cached Spotify transcript artifact."""
    matches = [configured for configured in enabled_sources(source) if configured.id == source]
    if not matches:
        raise typer.BadParameter(f"Unknown or disabled source: {source}")
    configured = matches[0]
    provider = configured.transcript_provider or "usetranscribe"
    if provider != "usetranscribe":
        raise typer.BadParameter(f"Unsupported transcript provider for {source}: {provider}")
    store = _store()
    try:
        result = UseTranscribeClient().transcribe_url(url)
        artifact = write_transcript_raw_artifact(result, configured, DATA_DIR / "raw")
        created = store.upsert_raw(artifact)
        store.log_run("transcribe", {"source": source, "url": url, "artifact": artifact.id, "created": created})
    finally:
        store.close()
    console.print(f"Wrote {artifact.raw_path}")


@app.command("run-weekly")
def run_weekly(send_email: Annotated[bool, typer.Option("--send", help="Send email after the brief.")] = False) -> None:
    """Run the local weekly pipeline without email unless explicitly requested."""
    ingest()
    normalize()
    extract()
    edit()
    target_week = current_week()
    brief(week=target_week)
    belief_update(week=target_week)
    if send_email:
        send(week=target_week)


@app.command("show-json")
def show_json(path: Path) -> None:
    """Debug helper for local artifact inspection."""
    console.print_json(data=read_json(path))
