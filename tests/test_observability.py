from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from app import cli
from app.ingest.discovery import DiscoveredItem
from app.ingest.rss import ingest_discovered_articles
from app.models import NormalizedItem, RawArtifact, Source
from app.observability.run import RunContext, classify_exception
from app.store.db import StateStore
from app.time import LOCAL_TZ


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
    week_start = datetime(2026, 7, 20, tzinfo=UTC)
    seen_window_starts = []

    def fake_enabled_sources(source_id=None):
        sources = [good, blocked]
        return [source for source in sources if source_id is None or source.id == source_id]

    def fake_discover(source, window, limit=5):
        seen_window_starts.append(window.start)
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

    def fake_ingest_articles(source, items, raw_root, run_context=None):
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
    monkeypatch.setattr(cli, "current_week_start", lambda: week_start)

    result = CliRunner().invoke(cli.app, ["run-weekly"])

    assert result.exit_code == 0, result.output
    run_dirs = list((data_dir / "runs").iterdir())
    assert len(run_dirs) == 1
    summary = json.loads((run_dirs[0] / "summary.json").read_text())
    manifest = json.loads((run_dirs[0] / "manifest.json").read_text())
    assert summary["source_outcomes"] == {"success": 1, "blocked_auth": 1}
    assert summary["stage_outcomes"]["skipped_config"] == 3
    assert summary["artifact_counts"]["ingest_written"] == 1
    assert seen_window_starts == [week_start, week_start]
    assert manifest["window"]["since"] == week_start.isoformat()
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


def test_run_weekly_historical_week_uses_bounded_window_and_records_target_week(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    db_path = data_dir / "state.sqlite3"
    source = _source("historical")
    seen_windows = []

    def fake_enabled_sources(source_id=None):
        return [source]

    def fake_discover(configured, window, limit=5):
        seen_windows.append(window)
        return []

    monkeypatch.setattr(cli, "DATA_DIR", data_dir)
    monkeypatch.setattr(cli, "DB_PATH", db_path)
    monkeypatch.setattr(cli, "enabled_sources", fake_enabled_sources)
    monkeypatch.setattr(cli, "discover_source", fake_discover)
    monkeypatch.setattr(cli, "current_week_start", lambda: datetime(2026, 7, 20, tzinfo=UTC))

    result = CliRunner().invoke(cli.app, ["run-weekly", "--week", "2026-W29"])

    assert result.exit_code == 0, result.output
    assert len(seen_windows) == 1
    assert seen_windows[0].start == datetime(2026, 7, 13, tzinfo=LOCAL_TZ)
    assert seen_windows[0].end == datetime(2026, 7, 19, 23, 59, 59, 999999, tzinfo=LOCAL_TZ)
    run_dir = next((data_dir / "runs").iterdir())
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["options"]["week"] == "2026-W29"
    assert manifest["window"] == {
        "since": "2026-07-13T00:00:00-07:00",
        "until": "2026-07-19T23:59:59.999999-07:00",
    }


@pytest.mark.parametrize("week", ["2026-W54", "2027-W01"])
def test_run_weekly_rejects_invalid_or_future_week_before_source_fetch(tmp_path, monkeypatch, week) -> None:
    monkeypatch.setattr(cli, "current_week_start", lambda: datetime(2026, 7, 20, tzinfo=UTC))
    monkeypatch.setattr(cli, "enabled_sources", lambda *_args, **_kwargs: pytest.fail("source fetch should not begin"))

    result = CliRunner().invoke(cli.app, ["run-weekly", "--week", week])

    assert result.exit_code != 0


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

    def fake_ingest_articles(source, items, raw_root, run_context=None):
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


def test_openai_news_ingest_skips_blocked_article_and_continues(tmp_path, monkeypatch) -> None:
    source = Source(
        id="openai_news",
        name="OpenAI News",
        lane="product_patterns",
        type="lab_product_and_research_updates",
        adapter="rss_or_html",
        source_url="https://openai.com/news/",
        rss_url="https://openai.com/news/rss.xml",
    )
    items = [
        DiscoveredItem(
            source_id=source.id,
            title="Blocked OpenAI Article",
            url="https://openai.com/index/blocked",
            item_type="article",
            published_at=datetime(2026, 7, 23, tzinfo=UTC),
            metadata={"discovered_via": "https://openai.com/news/rss.xml"},
        ),
        DiscoveredItem(
            source_id=source.id,
            title="Fetchable OpenAI Article",
            url="https://openai.com/index/fetchable",
            item_type="article",
            published_at=datetime(2026, 7, 22, tzinfo=UTC),
            metadata={"discovered_via": "https://openai.com/news/rss.xml"},
        ),
    ]

    def fake_get(url, **kwargs):
        assert kwargs["headers"]["User-Agent"].startswith("ai-intuition-compiler/")
        request = httpx.Request("GET", str(url))
        if str(url).endswith("/blocked"):
            return httpx.Response(403, request=request)
        return httpx.Response(
            200,
            text="<html><title>Fetchable</title><p>OpenAI product systems need explicit contracts.</p></html>",
            request=request,
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    context = RunContext("test-openai-news", tmp_path / "data", run_id="openai-news-item-skip")
    context.start()

    artifacts = ingest_discovered_articles(source, items, tmp_path / "data/raw", run_context=context)

    assert len(artifacts) == 1
    assert artifacts[0].title == "Fetchable OpenAI Article"
    assert artifacts[0].url == "https://openai.com/index/fetchable"

    skipped = [event for event in context.events if event.event_type == "item_skipped"]
    assert len(skipped) == 1
    assert skipped[0].source_id == "openai_news"
    assert skipped[0].url == "https://openai.com/index/blocked"
    assert skipped[0].metadata["outcome"] == "blocked_auth"
    assert skipped[0].metadata["retryability"] == "operator_action_required"


def test_extract_skips_rejected_normalized_artifacts_with_diagnostics(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    db_path = data_dir / "state.sqlite3"
    monkeypatch.setattr(cli, "DATA_DIR", data_dir)
    monkeypatch.setattr(cli, "DB_PATH", db_path)
    store = StateStore(db_path)
    item = NormalizedItem(
        id="paywall",
        raw_artifact_id="paywall",
        source_id="stratechery",
        source_name="Stratechery",
        source_type="html",
        lane="strategy_value_capture",
        title="Paywalled article",
        url="https://stratechery.com/2026/example",
        published_at=datetime(2026, 7, 24, tzinfo=UTC),
        raw_path="data/raw/lab-posts/paywall.html",
        normalized_path=str(data_dir / "normalized/paywall.md"),
        text="Subscribe to Stratechery Plus for full access.",
        word_count=7,
        detected_page_type="partial_paywalled_page",
        primary_content_kind="paywall_copy",
        selected_normalizer="stratechery_paywall_detector",
        quality_status="rejected",
        quality_flags=["paywall_dominant"],
        degraded_reason="Paywall copy.",
    )
    context = RunContext("test-extract-skip", data_dir, run_id="extract-skip")
    context.start()
    try:
        store.upsert_normalized(item)
        count = cli._run_extract(store, mode=cli.ExtractionMode.codex_packet, run_context=context)
    finally:
        store.close()

    assert count == 0
    assert not (data_dir / "extraction-packets/paywall.md").exists()
    skipped = [event for event in context.events if event.event_type == "extraction_skipped"]
    assert len(skipped) == 1
    assert skipped[0].metadata["quality_status"] == "rejected"
    assert skipped[0].metadata["quality_flags"] == ["paywall_dominant"]


def test_normalize_quality_event_includes_fallback_diagnostics(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    db_path = data_dir / "state.sqlite3"
    raw_path = data_dir / "raw/lab-posts/example.html"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("<html><body><p>" + " ".join(["article"] * 300) + "</p></body></html>")
    artifact = RawArtifact(
        id="fallback-example",
        source_id="example",
        source_name="Example",
        source_type="html",
        lane="frontier_primitives",
        title="Example",
        url="https://example.com/article",
        discovered_at=datetime(2026, 7, 25, tzinfo=UTC),
        raw_path=str(raw_path),
        content_hash="fallback-hash",
        metadata={
            "detected_page_type": "article_page",
            "primary_content_kind": "article_body",
            "selected_normalizer": "generic_html_fallback",
            "classification_confidence": 0.4,
            "classification_signals": ["generic_html_fallback"],
            "quality_flags": ["generic_fallback_used"],
            "fallback_attempts": ["generic_html_fallback"],
            "selected_fallback": "generic_html_fallback",
        },
    )
    monkeypatch.setattr(cli, "DATA_DIR", data_dir)
    monkeypatch.setattr(cli, "DB_PATH", db_path)
    context = RunContext("normalize", data_dir, run_id="fallback-diagnostics")
    context.start()
    store = StateStore(db_path)
    try:
        store.upsert_raw(artifact)
        cli._run_normalize(store, run_context=context)
    finally:
        store.close()

    event = next(event for event in context.events if event.event_type == "quality_checked")
    assert event.metadata["fallback_attempts"] == ["generic_html_fallback"]
    assert event.metadata["selected_fallback"] == "generic_html_fallback"

    store = StateStore(db_path)
    try:
        stored_raw = store.list_raw("fallback-example")[0]
    finally:
        store.close()
    assert stored_raw.metadata["quality_status"] == "usable"
    assert stored_raw.metadata["word_count"] == 300
    assert stored_raw.metadata["selected_fallback"] == "generic_html_fallback"


def test_openai_research_rss_failure_records_selected_path_and_filter(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    source = Source(
        id="openai_research",
        name="OpenAI Research",
        lane="frontier_primitives",
        type="lab_research",
        adapter="openai_research_rss",
        rss_url="https://openai.com/news/rss.xml",
    )
    monkeypatch.setattr(cli, "DATA_DIR", data_dir)
    monkeypatch.setattr(cli, "DB_PATH", data_dir / "state.sqlite3")
    monkeypatch.setattr(cli, "enabled_sources", lambda source_id=None: [source])
    monkeypatch.setattr(cli, "discover_source", lambda *_args, **_kwargs: (_ for _ in ()).throw(_http_error(403)))
    context = RunContext("ingest", data_dir, run_id="openai-research-rss-failure")
    context.start()
    store = StateStore(data_dir / "state.sqlite3")
    try:
        cli._run_ingest(store, source="openai_research", run_context=context)
    finally:
        store.close()

    attempt = context.source_attempts[0]
    assert attempt.outcome == "blocked_auth"
    assert attempt.metadata["selected_discovery_path"] == "https://openai.com/news/rss.xml"
    assert attempt.metadata["category_filter"] == "Research"
    assert attempt.error is not None
    assert attempt.error.context["adapter_policy"] == "openai_research_rss"
