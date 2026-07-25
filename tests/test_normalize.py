from __future__ import annotations

from datetime import UTC, datetime

from app.models import RawArtifact
from app.normalize.normalize import normalize_raw_artifact
from app.store.files import read_markdown


def test_normalized_item_uses_repo_relative_raw_path(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    raw_path = tmp_path / "data/raw/lab-posts/example.html"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("<html><title>Example</title><p>Agents need harnesses.</p></html>")
    artifact = RawArtifact(
        id="example",
        source_id="anthropic_research",
        source_name="Anthropic Research",
        lane="reliability_failures",
        source_type="html",
        title="Example",
        url="https://example.com/article",
        published_at=datetime(2026, 7, 24, tzinfo=UTC),
        discovered_at=datetime(2026, 7, 25, tzinfo=UTC),
        raw_path=str(raw_path),
        content_hash="hash",
    )

    normalized = normalize_raw_artifact(artifact, tmp_path / "data/normalized")
    metadata, _ = read_markdown(tmp_path / normalized.normalized_path)

    assert normalized.raw_path == "data/raw/lab-posts/example.html"
    assert metadata["raw_path"] == "data/raw/lab-posts/example.html"
    assert metadata["quality_status"] == "usable"
    assert "low_word_count" in metadata["quality_flags"]


def test_stratechery_paywall_artifact_is_rejected_for_extraction(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    raw_path = tmp_path / "data/raw/lab-posts/stratechery.html"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        """
<html><title>Strategy update</title><body>
  <h1>Strategy update</h1>
  <p>Subscribe to Stratechery Plus for full access.</p>
  <p>Already subscribed?</p>
  <p>$15 / month or $150 / year</p>
</body></html>
"""
    )
    artifact = RawArtifact(
        id="stratechery_paywall",
        source_id="stratechery",
        source_name="Stratechery",
        lane="strategy_value_capture",
        source_type="html",
        title="Strategy update",
        url="https://stratechery.com/2026/example",
        published_at=datetime(2026, 7, 24, tzinfo=UTC),
        discovered_at=datetime(2026, 7, 25, tzinfo=UTC),
        raw_path=str(raw_path),
        content_hash="hash",
    )

    normalized = normalize_raw_artifact(artifact, tmp_path / "data/normalized")
    metadata, _ = read_markdown(tmp_path / normalized.normalized_path)

    assert normalized.quality_status == "rejected"
    assert normalized.primary_content_kind == "paywall_copy"
    assert "paywall_dominant" in normalized.quality_flags
    assert metadata["quality_status"] == "rejected"


def test_historical_lenny_media_html_normalizes_as_degraded_show_notes(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    raw_path = tmp_path / "data/raw/lab-posts/lenny.html"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        """
<html><body>
  <h1>Computer and browser use in Codex</h1>
  <p>What you'll learn: short show notes.</p>
  <iframe src="https://www.youtube.com/embed/t0GiTyz4syY"></iframe>
  <script>{"transcription":{"cdn_url":"https://substackcdn.com/video_upload/post/1/media/transcription.json?Expires=1"}}</script>
</body></html>
"""
    )
    artifact = RawArtifact(
        id="lenny_show_notes",
        source_id="lenny_newsletter",
        source_name="Lenny's Newsletter",
        lane="product_patterns",
        source_type="html",
        title="Computer and browser use in Codex",
        url="https://www.lennysnewsletter.com/p/computer-and-browser-use-in-codex",
        published_at=datetime(2026, 7, 22, tzinfo=UTC),
        discovered_at=datetime(2026, 7, 25, tzinfo=UTC),
        raw_path=str(raw_path),
        content_hash="hash",
    )

    normalized = normalize_raw_artifact(artifact, tmp_path / "data/normalized")

    assert normalized.detected_page_type == "hybrid_media_post"
    assert normalized.primary_content_kind == "show_notes"
    assert normalized.quality_status == "degraded"
    assert "show_notes_without_transcript" in normalized.quality_flags
