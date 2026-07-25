from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
from typer.testing import CliRunner

from app import cli
from app.ingest.discovery import DiscoveredItem
from app.models import RawArtifact, Source
from app.observability.run import RunContext, classify_exception
from app.store.db import StateStore


def _http_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.com/source")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(f"{status_code} error", request=request, response=response)


def _source(source_id: str) -> Source:
    return Source(
        id=source_id,
        name=source_id.title(),
        lane="frontier_primitives",
        type="lab_research",
        source_url=f"https://example.com/{source_id}",
        adapter="html_index",
    )


def test_failure_classification_covers_common_source_and_transcript_failures() -> None:
    assert classify_exception(_http_error(403))[0:2] == ("blocked_auth", "operator_action_required")
    assert classify_exception(_http_error(429))[0:2] == ("rate_limited", "retryable")
    assert classify_exception(_http_error(404))[0:2] == ("not_found", "permanent")
    assert classify_exception(RuntimeError("spotify_not_cached: missing cached transcript"))[0:2] == ("not_found", "permanent")
    assert classify_exception(RuntimeError("unsupported_url: Spotify is no longer supported"))[0:2] == ("blocked_provider", "permanent")
    assert classify_exception(RuntimeError("transcription_failed: provider error"))[0:2] == ("network_failure", "retryable")
    assert classify_exception(ValueError("malformed RSS payload"))[0:2] == ("malformed_source", "bug_likely")
    assert classify_exception(ValueError("malformed HTML/no article candidates"))[0:2] == ("malformed_source", "bug_likely")


def test_run_context_writes_events_summary_report_and_persists_to_sqlite(tmp_path) -> None:
    data_dir = tmp_path / "data"
    context = RunContext("run-weekly", data_dir, options={"extraction_mode": "codex_packet"}, run_id="test-run")
    source = _source("blocked")

    context.start()
    outcome, retryability, error = classify_exception(_http_error(403))
    context.record_source_attempt(
        source,
        stage="ingest",
        urls_attempted=source.urls,
        item_count=0,
        artifact_count=0,
        elapsed_ms=3,
        outcome=outcome,
        retryability=retryability,
        error=error,
    )
    context.record_stage_skip("edit", "Skipped edit in packet mode.")
    summary = context.finish()

    run_dir = data_dir / "runs" / "test-run"
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "events.jsonl").exists()
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "failure_report.md").exists()
    assert json.loads((run_dir / "summary.json").read_text())["source_outcomes"] == {"blocked_auth": 1}
    assert "Check credentials" in (run_dir / "failure_report.md").read_text()

    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    assert {event["event_type"] for event in events} >= {"run_started", "source_failed", "run_finished"}

    store = StateStore(tmp_path / "state.sqlite3")
    try:
        store.upsert_run_summary(summary)
        store.insert_source_attempts(context.source_attempts)
        store.insert_stage_attempts(context.stage_results)
        row = store.conn.execute("SELECT payload_json FROM run_summaries WHERE run_id = ?", ("test-run",)).fetchone()
        source_rows = store.conn.execute("SELECT COUNT(*) AS count FROM source_attempts WHERE run_id = ?", ("test-run",)).fetchone()
        stage_rows = store.conn.execute("SELECT COUNT(*) AS count FROM stage_attempts WHERE run_id = ?", ("test-run",)).fetchone()
    finally:
        store.close()

    assert row is not None
    assert source_rows["count"] == 1
    assert stage_rows["count"] == 1


def test_run_weekly_records_partial_success_and_packet_skips(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    db_path = data_dir / "state.sqlite3"
    good = _source("good")
    blocked = _source("blocked")

    def fake_enabled_sources(source_id=None):
        sources = [good, blocked]
        return [source for source in sources if source_id is None or source.id == source_id]

    def fake_discover(source, window, limit=5):
        if source.id == "blocked":
            raise _http_error(403)
        return [
            DiscoveredItem(
                source_id=source.id,
                title="Useful article",
                url="https://example.com/good/article",
                item_type="article",
                published_at=datetime(2026, 7, 24, tzinfo=UTC),
            )
        ]

    def fake_ingest_articles(source, items, raw_root):
        raw_path = data_dir / "raw" / "lab-posts" / "good.html"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text("<html><title>Useful article</title><p>Agents need structured run logs.</p></html>")
        return [
            RawArtifact(
                id="good_article",
                source_id=source.id,
                source_name=source.name,
                lane=source.lane,
                source_type=source.type,
                title="Useful article",
                url="https://example.com/good/article",
                published_at=datetime(2026, 7, 24, tzinfo=UTC),
                discovered_at=datetime(2026, 7, 25, tzinfo=UTC),
                raw_path=str(raw_path),
                content_hash="good-hash",
            )
        ]

    monkeypatch.setattr(cli, "DATA_DIR", data_dir)
    monkeypatch.setattr(cli, "DB_PATH", db_path)
    monkeypatch.setattr(cli, "enabled_sources", fake_enabled_sources)
    monkeypatch.setattr(cli, "discover_source", fake_discover)
    monkeypatch.setattr(cli, "ingest_discovered_articles", fake_ingest_articles)

    result = CliRunner().invoke(cli.app, ["run-weekly"])

    assert result.exit_code == 0, result.output
    run_dirs = list((data_dir / "runs").iterdir())
    assert len(run_dirs) == 1
    summary = json.loads((run_dirs[0] / "summary.json").read_text())
    assert summary["source_outcomes"] == {"success": 1, "blocked_auth": 1}
    assert summary["stage_outcomes"]["skipped_config"] == 3
    assert summary["artifact_counts"]["ingest_written"] == 1
    assert summary["artifact_counts"]["extract_written"] == 1
    assert summary["failure_report_path"]

    events = [json.loads(line) for line in (run_dirs[0] / "events.jsonl").read_text().splitlines()]
    event_types = {event["event_type"] for event in events}
    assert {"stage_started", "stage_finished", "source_attempt_started", "source_failed", "artifact_written"} <= event_types

    store = StateStore(db_path)
    try:
        attempts = store.conn.execute("SELECT outcome FROM source_attempts ORDER BY source_id").fetchall()
        stages = store.conn.execute("SELECT stage, outcome FROM stage_attempts").fetchall()
    finally:
        store.close()

    assert [row["outcome"] for row in attempts] == ["blocked_auth", "success"]
    assert ("edit", "skipped_config") in [(row["stage"], row["outcome"]) for row in stages]


def test_run_weekly_idempotent_artifact_events_on_second_run(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    db_path = data_dir / "state.sqlite3"
    source = _source("good")

    def fake_enabled_sources(source_id=None):
        return [source]

    def fake_discover(source, window, limit=5):
        return [
            DiscoveredItem(
                source_id=source.id,
                title="Useful article",
                url="https://example.com/good/article",
                item_type="article",
                published_at=datetime(2026, 7, 24, tzinfo=UTC),
            )
        ]

    def fake_ingest_articles(source, items, raw_root):
        raw_path = data_dir / "raw" / "lab-posts" / "good.html"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text("<html><title>Useful article</title><p>Same content.</p></html>")
        return [
            RawArtifact(
                id="good_article",
                source_id=source.id,
                source_name=source.name,
                lane=source.lane,
                source_type=source.type,
                title="Useful article",
                url="https://example.com/good/article",
                published_at=datetime(2026, 7, 24, tzinfo=UTC),
                discovered_at=datetime(2026, 7, 25, tzinfo=UTC),
                raw_path=str(raw_path),
                content_hash="good-hash",
            )
        ]

    monkeypatch.setattr(cli, "DATA_DIR", data_dir)
    monkeypatch.setattr(cli, "DB_PATH", db_path)
    monkeypatch.setattr(cli, "enabled_sources", fake_enabled_sources)
    monkeypatch.setattr(cli, "discover_source", fake_discover)
    monkeypatch.setattr(cli, "ingest_discovered_articles", fake_ingest_articles)

    runner = CliRunner()
    assert runner.invoke(cli.app, ["run-weekly"]).exit_code == 0
    assert runner.invoke(cli.app, ["run-weekly"]).exit_code == 0

    summaries = [json.loads((run_dir / "summary.json").read_text()) for run_dir in (data_dir / "runs").iterdir()]
    artifact_counts = [summary["artifact_counts"] for summary in summaries]
    assert any(counts.get("ingest_written") == 1 for counts in artifact_counts)
    assert any(counts.get("ingest_unchanged") == 1 and "extract_unchanged" in counts for counts in artifact_counts)
