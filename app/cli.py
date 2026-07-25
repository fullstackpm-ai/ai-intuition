from __future__ import annotations

import os
import time
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from app.artifacts import build_artifact_report, render_artifact_report_markdown
from app.config import DATA_DIR, DB_PATH, enabled_sources
from app.ingest.discovery import DateWindow, discover_source
from app.ingest.manual import ingest_manual_directory, ingest_manual_file
from app.ingest.rss import ingest_discovered_articles, ingest_discovered_podcast_pages
from app.ingest.transcript import UseTranscribeClient, write_transcript_raw_artifact
from app.llm.belief_update import update_beliefs
from app.llm.edit import edit_insights
from app.llm.extract import build_extraction_packet, extract_insights, import_insights_from_json
from app.llm.synthesize import build_weekly_brief
from app.logging import console
from app.models import ExtractedInsight, Source
from app.normalize.normalize import normalize_raw_artifact
from app.observability import RunContext, classify_exception
from app.store.db import StateStore
from app.store.files import ensure_data_dirs, read_json, write_json
from app.time import current_week, now_local, parse_since

app = typer.Typer(help="AI Intuition Compiler CLI")


class ExtractionMode(str, Enum):
    mock = "mock"
    api = "api"
    codex_packet = "codex_packet"


class ImportExtractionMethod(str, Enum):
    api = "api"
    codex_packet = "codex_packet"
    manual = "manual"


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


def _write_insight_artifacts(insights: list[ExtractedInsight]) -> None:
    by_item: dict[str, list[object]] = {}
    rejected_by_item: dict[str, list[object]] = {}
    for insight in insights:
        target = rejected_by_item if insight.status == "rejected" else by_item
        target.setdefault(insight.item_id, []).append(insight.model_dump(mode="json"))
    for item_id, payload in by_item.items():
        write_json(DATA_DIR / "extracted" / f"{item_id}.json", payload)
    for item_id, payload in rejected_by_item.items():
        write_json(DATA_DIR / "rejected" / f"{item_id}.json", payload)


def _write_extraction_packet(item_id: str, body: str) -> tuple[Path, bool]:
    path = DATA_DIR / "extraction-packets" / f"{item_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = body + "\n"
    changed = not path.exists() or path.read_text() != payload
    path.write_text(payload)
    return path, changed


def _source_urls(configured: Source) -> list[str]:
    if configured.rss_url_env and os.getenv(configured.rss_url_env):
        configured.urls = [os.environ[configured.rss_url_env], *[url for url in configured.urls if url != os.environ[configured.rss_url_env]]]
    return configured.urls or ([configured.path] if configured.path else [])


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _run_ingest(
    store: StateStore,
    since: str = "7d",
    source: str | None = None,
    manual: Path | None = None,
    run_context: RunContext | None = None,
) -> int:
    created = 0
    window = DateWindow(start=parse_since(since), end=now_local())
    if manual:
        configured = _manual_source()
        started = time.perf_counter()
        if run_context:
            run_context.event("ingest", "source_attempt_started", "Manual file ingest started.", source=configured, url=str(manual))
        artifact = ingest_manual_file(manual, configured, DATA_DIR / "raw")
        changed = store.upsert_raw(artifact)
        created += int(changed)
        if run_context:
            run_context.record_artifact("ingest", artifact.raw_path, artifact.id, changed)
            run_context.record_source_attempt(
                configured,
                stage="ingest",
                urls_attempted=[str(manual)],
                item_count=1,
                artifact_count=1,
                elapsed_ms=_elapsed_ms(started),
                outcome="success",
            )
        store.log_run("ingest", {"since": since, "source": source, "manual": str(manual), "created": created})
        return created

    for configured in enabled_sources(source):
        started = time.perf_counter()
        adapter = configured.adapter or configured.type
        urls_attempted = _source_urls(configured)
        source_artifacts = []
        item_count = 0
        if run_context:
            run_context.event(
                "ingest",
                "source_attempt_started",
                f"Source {configured.id} ingest started.",
                source=configured,
                url=urls_attempted[0] if urls_attempted else None,
                metadata={"urls_attempted": urls_attempted},
            )
        try:
            if adapter == "manual" or configured.type == "manual":
                source_artifacts = ingest_manual_directory(configured, Path.cwd())
                item_count = len(source_artifacts)
            elif adapter in {"rss_or_html", "html_index"}:
                discovered = discover_source(configured, window, limit=5)
                item_count = len(discovered)
                source_artifacts = ingest_discovered_articles(configured, discovered, DATA_DIR / "raw")
            elif adapter == "podcast_episode_page_or_youtube":
                discovered = discover_source(configured, window, limit=5)
                item_count = len(discovered)
                source_artifacts = ingest_discovered_podcast_pages(
                    configured,
                    discovered,
                    DATA_DIR / "raw",
                    run_context=run_context,
                )
            else:
                if run_context:
                    run_context.event(
                        "ingest",
                        "source_skipped",
                        f"Unsupported adapter skipped: {adapter}.",
                        source=configured,
                        metadata={"outcome": "skipped_config", "adapter": adapter},
                    )
                    run_context.record_source_attempt(
                        configured,
                        stage="ingest",
                        urls_attempted=urls_attempted,
                        item_count=0,
                        artifact_count=0,
                        elapsed_ms=_elapsed_ms(started),
                        outcome="skipped_config",
                    )
                continue
            source_created = 0
            for artifact in source_artifacts:
                changed = store.upsert_raw(artifact)
                created += int(changed)
                source_created += int(changed)
                if run_context:
                    run_context.record_artifact("ingest", artifact.raw_path, artifact.id, changed)
            outcome = "healthy_empty" if item_count == 0 and not source_artifacts else "success"
            if run_context:
                run_context.record_source_attempt(
                    configured,
                    stage="ingest",
                    urls_attempted=urls_attempted,
                    item_count=item_count,
                    artifact_count=len(source_artifacts),
                    elapsed_ms=_elapsed_ms(started),
                    outcome=outcome,
                    metadata={"created": source_created},
                )
        except Exception as exc:  # Network sources should not block weekly pipeline progress.
            console.print(f"[yellow]Skipped {configured.id}: {exc}[/yellow]")
            if run_context:
                outcome, retryability, error = classify_exception(exc)
                error.context = {"source_id": configured.id, "adapter": adapter, "urls_attempted": urls_attempted}
                run_context.record_source_attempt(
                    configured,
                    stage="ingest",
                    urls_attempted=urls_attempted,
                    item_count=item_count,
                    artifact_count=len(source_artifacts),
                    elapsed_ms=_elapsed_ms(started),
                    outcome=outcome,
                    retryability=retryability,
                    error=error,
                )
    store.log_run("ingest", {"since": since, "source": source, "manual": None, "created": created})
    return created


def _run_normalize(store: StateStore, since: str = "7d", item: str | None = None, run_context: RunContext | None = None) -> int:
    count = 0
    for artifact in store.list_raw(item):
        normalized = normalize_raw_artifact(artifact, DATA_DIR / "normalized")
        store.upsert_normalized(normalized)
        count += 1
        if run_context:
            run_context.record_artifact("normalize", normalized.normalized_path, normalized.id, True)
    store.log_run("normalize", {"since": since, "item": item, "count": count})
    return count


def _run_extract(
    store: StateStore,
    since: str = "7d",
    item: str | None = None,
    mode: ExtractionMode = ExtractionMode.mock,
    run_context: RunContext | None = None,
) -> int:
    count = 0
    if mode == ExtractionMode.api:
        raise typer.BadParameter("API extraction is not implemented yet. Use --mode codex_packet or --mode mock.")
    for normalized in store.list_normalized(item):
        if mode == ExtractionMode.codex_packet:
            path, changed = _write_extraction_packet(normalized.id, build_extraction_packet(normalized))
            count += 1
            if run_context:
                run_context.record_artifact("extract", str(path), normalized.id, changed)
            continue
        insights = extract_insights(normalized, extraction_method="mock")
        _write_insight_artifacts(insights)
        store.upsert_insights(insights)
        count += len(insights)
        if run_context:
            run_context.record_artifact("extract", str(DATA_DIR / "extracted" / f"{normalized.id}.json"), normalized.id, True)
    store.log_run("extract", {"since": since, "item": item, "mode": mode.value, "count": count})
    return count


def _run_edit(store: StateStore, since: str = "7d", run_context: RunContext | None = None) -> int:
    insights = store.list_insights()
    edited = edit_insights(insights)
    _write_insight_artifacts(edited)
    store.upsert_insights(edited)
    store.log_run("edit", {"since": since, "count": len(edited)})
    if run_context:
        run_context.artifact_counts["edit_written"] += len(edited)
    return len(insights)


def _run_brief(store: StateStore, week: str | None = None, current_week_flag: bool = False, run_context: RunContext | None = None) -> Path:
    target_week = current_week() if current_week_flag or not week else week
    _, path = build_weekly_brief(target_week, store.list_insights(), DATA_DIR / "briefs")
    store.log_run("brief", {"week": target_week, "path": str(path)})
    if run_context:
        run_context.record_artifact("brief", str(path), target_week, True)
    return path


def _run_belief_update(store: StateStore, week: str | None = None, current_week_flag: bool = False, run_context: RunContext | None = None) -> list[Path]:
    target_week = current_week() if current_week_flag or not week else week
    touched = update_beliefs(target_week, store.list_insights(), DATA_DIR / "beliefs")
    store.log_run("belief-update", {"week": target_week, "touched": [str(path) for path in touched]})
    if run_context:
        for path in touched:
            run_context.record_artifact("belief_update", str(path), path.stem, True)
    return touched


@app.command()
def ingest(
    since: Annotated[str, typer.Option(help="Only ingest discovered items newer than this window when publish dates are available.")] = "7d",
    source: Annotated[str | None, typer.Option(help="Source id to ingest.")] = None,
    manual: Annotated[Path | None, typer.Option(help="Manual markdown source to ingest.")] = None,
) -> None:
    """Save raw artifacts and update SQLite without calling the LLM."""
    store = _store()
    try:
        created = _run_ingest(store, since=since, source=source, manual=manual)
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
    try:
        count = _run_normalize(store, since=since, item=item)
    finally:
        store.close()
    console.print(f"Normalized {count} item(s).")


@app.command()
def extract(
    since: Annotated[str, typer.Option(help="Currently accepted for command compatibility.")] = "7d",
    item: Annotated[str | None, typer.Option(help="Normalized item id to extract.")] = None,
    mode: Annotated[ExtractionMode, typer.Option(help="Extraction mode: mock for tests, codex_packet for Codex harness, api for future API-backed extraction.")] = ExtractionMode.mock,
) -> None:
    """Extract insights or write Codex-ready extraction packets."""
    store = _store()
    try:
        count = _run_extract(store, since=since, item=item, mode=mode)
    finally:
        store.close()
    if mode == ExtractionMode.codex_packet:
        console.print(f"Wrote {count} extraction packet(s).")
    else:
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
            _write_extraction_packet(normalized.id, build_extraction_packet(normalized))
            count += 1
        store.log_run("extract-packet", {"item": item, "count": count})
    finally:
        store.close()
    console.print(f"Wrote {count} extraction packet(s).")


@app.command("import-extraction")
def import_extraction(
    item: Annotated[str, typer.Option(help="Normalized item id for the imported extraction.")],
    path: Annotated[Path, typer.Option(help="JSON file containing a list of extracted insight objects.")],
    method: Annotated[ImportExtractionMethod, typer.Option(help="Provenance for imported extraction JSON.")] = ImportExtractionMethod.codex_packet,
) -> None:
    """Validate and import Codex/API-authored extraction JSON into artifacts and SQLite."""
    store = _store()
    try:
        matches = store.list_normalized(item)
        if not matches:
            raise typer.BadParameter(f"Unknown normalized item id: {item}")
        insights = import_insights_from_json(
            matches[0],
            path,
            extraction_method=method.value,
            extraction_model="codex" if method == ImportExtractionMethod.codex_packet else method.value,
        )
        _write_insight_artifacts(insights)
        store.upsert_insights(insights)
        store.log_run("import-extraction", {"item": item, "path": str(path), "method": method.value, "count": len(insights)})
    finally:
        store.close()
    console.print(f"Imported {len(insights)} insight(s).")


@app.command()
def edit(since: Annotated[str, typer.Option(help="Currently accepted for command compatibility.")] = "7d") -> None:
    """Apply adversarial editor scoring rules to candidate insights."""
    store = _store()
    try:
        count = _run_edit(store, since=since)
    finally:
        store.close()
    console.print(f"Edited {count} insight(s).")


@app.command()
def brief(
    week: Annotated[str | None, typer.Option(help="ISO week, e.g. 2026-W22.")] = None,
    current_week_flag: Annotated[bool, typer.Option("--current-week", help="Use the current ISO week.")] = False,
) -> None:
    """Generate a markdown weekly brief from accepted extracted JSON."""
    target_week = current_week() if current_week_flag or not week else week
    store = _store()
    try:
        path = _run_brief(store, week=target_week)
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
        touched = _run_belief_update(store, week=target_week)
    finally:
        store.close()
    console.print(f"Updated {len(touched)} belief file(s).")


@app.command("artifact-report")
def artifact_report(
    json_output: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON instead of markdown.")] = False,
) -> None:
    """Classify weekly run artifacts by repo retention and organization policy."""
    report = build_artifact_report(Path.cwd(), data_dir=DATA_DIR)
    if json_output:
        console.print_json(data=report.model_dump(mode="json"))
        return
    console.print(render_artifact_report_markdown(report))


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
def run_weekly(
    send_email: Annotated[bool, typer.Option("--send", help="Send email after the brief.")] = False,
    extraction_mode: Annotated[ExtractionMode, typer.Option(help="Extraction mode for the weekly run. Defaults to Codex packet mode so weekly runs do not silently create mock-derived briefs.")] = ExtractionMode.codex_packet,
) -> None:
    """Run the local weekly pipeline without email unless explicitly requested."""
    run_context = RunContext(
        "run-weekly",
        DATA_DIR,
        options={"send": send_email, "extraction_mode": extraction_mode.value, "window": {"since": "7d"}},
    )
    run_context.start()
    store = _store()
    try:
        with run_context.stage("ingest"):
            created = _run_ingest(store, run_context=run_context)
        console.print(f"Ingested {created} new raw artifact(s).")
        with run_context.stage("normalize"):
            normalized = _run_normalize(store, run_context=run_context)
        console.print(f"Normalized {normalized} item(s).")
        with run_context.stage("extract", {"mode": extraction_mode.value}):
            extracted = _run_extract(store, mode=extraction_mode, run_context=run_context)
        if extraction_mode == ExtractionMode.codex_packet:
            console.print(f"Wrote {extracted} extraction packet(s).")
            for skipped_stage in ["edit", "brief", "belief_update"]:
                run_context.record_stage_skip(
                    skipped_stage,
                    f"Skipped {skipped_stage}; import real extracted insight JSON before continuing.",
                    metadata={"reason": "codex_packet_requires_import"},
                )
            console.print("[yellow]Skipped edit, brief, and belief update. Import real extracted insight JSON, then run edit/brief/belief-update.[/yellow]")
            return
        console.print(f"Extracted {extracted} insight candidate(s).")
        with run_context.stage("edit"):
            edited = _run_edit(store, run_context=run_context)
        console.print(f"Edited {edited} insight(s).")
        target_week = current_week()
        with run_context.stage("brief", {"week": target_week}):
            path = _run_brief(store, week=target_week, run_context=run_context)
        console.print(f"Wrote {path}")
        with run_context.stage("belief_update", {"week": target_week}):
            touched = _run_belief_update(store, week=target_week, run_context=run_context)
        console.print(f"Updated {len(touched)} belief file(s).")
        if send_email:
            with run_context.stage("send", {"week": target_week}):
                send(week=target_week)
    finally:
        summary = run_context.finish()
        store.upsert_run_summary(summary)
        store.insert_source_attempts(run_context.source_attempts)
        store.insert_stage_attempts(run_context.stage_results)
        store.close()
        console.print(f"Wrote run diagnostics to {run_context.run_dir}")


@app.command("show-json")
def show_json(path: Path) -> None:
    """Debug helper for local artifact inspection."""
    console.print_json(data=read_json(path))
