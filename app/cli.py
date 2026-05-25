from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from app.config import DATA_DIR, DB_PATH, enabled_sources
from app.ingest.manual import ingest_manual_directory, ingest_manual_file
from app.ingest.rss import ingest_rss_or_html_source
from app.llm.belief_update import update_beliefs
from app.llm.edit import edit_insights
from app.llm.extract import extract_insights
from app.llm.synthesize import build_weekly_brief
from app.logging import console
from app.models import Source
from app.normalize.normalize import normalize_raw_artifact
from app.store.db import StateStore
from app.store.files import ensure_data_dirs, read_json, write_json
from app.time import current_week

app = typer.Typer(help="AI Operating Intelligence CLI")


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
    since: Annotated[str, typer.Option(help="Currently accepted for command compatibility.")] = "7d",
    source: Annotated[str | None, typer.Option(help="Source id to ingest.")] = None,
    manual: Annotated[Path | None, typer.Option(help="Manual markdown source to ingest.")] = None,
) -> None:
    """Save raw artifacts and update SQLite without calling the LLM."""
    store = _store()
    created = 0
    try:
        artifacts = []
        if manual:
            artifacts.append(ingest_manual_file(manual, _manual_source(), DATA_DIR / "raw"))
        else:
            for configured in enabled_sources(source):
                try:
                    if configured.type == "manual":
                        artifacts.extend(ingest_manual_directory(configured, Path.cwd()))
                    elif configured.type == "rss_or_html":
                        artifacts.extend(ingest_rss_or_html_source(configured, DATA_DIR / "raw"))
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
