from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.ingest.adapters import select_html_adapter
from app.ingest.discovery import DiscoveredItem
from app.ingest.rss import ingest_discovered_articles
from app.models import RawArtifact, Source
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


def test_google_research_article_adapter_removes_utility_noise_and_keeps_article_body(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = Source(id="google_research_blog", name="Google Research Blog", lane="frontier_primitives", type="research_blog")
    item = DiscoveredItem(
        source_id=source.id,
        title="SymptomAI",
        url="https://research.google/blog/symptomai/",
        item_type="article",
    )
    decision = select_html_adapter(source, item)
    raw_path = tmp_path / "data/raw/lab-posts/google.html"
    raw_path.parent.mkdir(parents=True)
    article_words = " ".join(["evidence"] * 700)
    raw_path.write_text(
        f"""
<html><head><title>SymptomAI</title></head><body>
  <nav>Quick links Share Copy link</nav>
  <article><h1>SymptomAI</h1><p>{article_words}</p><h2>Other posts of interest</h2><p>Related post noise.</p></article>
  <footer>Labels: AI</footer>
</body></html>
"""
    )
    artifact = RawArtifact(
        id="google_article",
        source_id=source.id,
        source_name=source.name,
        lane=source.lane,
        source_type="html",
        title=item.title,
        url=item.url,
        discovered_at=datetime(2026, 7, 25, tzinfo=UTC),
        raw_path=str(raw_path),
        content_hash="hash",
        metadata=decision.metadata,
    )

    normalized = normalize_raw_artifact(artifact, tmp_path / "data/normalized")

    assert normalized.selected_normalizer == "google_research_article"
    assert normalized.quality_status == "usable"
    assert normalized.word_count >= 700
    assert "Quick links" not in normalized.text
    assert "Related post noise." not in normalized.text


def test_anthropic_article_adapter_stays_usable_article_body(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = Source(id="anthropic_engineering", name="Anthropic Engineering", lane="product_patterns", type="engineering_blog")
    item = DiscoveredItem(
        source_id=source.id,
        title="How we contain Claude",
        url="https://www.anthropic.com/engineering/how-we-contain-claude",
        item_type="article",
    )
    decision = select_html_adapter(source, item)
    raw_path = tmp_path / "data/raw/lab-posts/anthropic.html"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("<html><body><article><h1>How we contain Claude</h1><p>" + " ".join(["containment"] * 500) + "</p></article></body></html>")
    artifact = RawArtifact(
        id="anthropic_article",
        source_id=source.id,
        source_name=source.name,
        lane=source.lane,
        source_type="html",
        title=item.title,
        url=item.url,
        discovered_at=datetime(2026, 7, 25, tzinfo=UTC),
        raw_path=str(raw_path),
        content_hash="hash",
        metadata=decision.metadata,
    )

    normalized = normalize_raw_artifact(artifact, tmp_path / "data/normalized")

    assert normalized.detected_page_type == "article_page"
    assert normalized.primary_content_kind == "article_body"
    assert normalized.selected_normalizer == "anthropic_article"
    assert normalized.quality_status == "usable"


def test_stratechery_authorized_full_feed_is_persisted_without_refetch(tmp_path, monkeypatch) -> None:
    source = Source(
        id="stratechery",
        name="Stratechery",
        lane="strategy_value_capture",
        type="strategy_newsletter",
        rss_url_env="STRATECHERY_PERSONAL_RSS_URL",
    )
    item = DiscoveredItem(
        source_id=source.id,
        title="Strategy update",
        url="https://stratechery.com/2026/example",
        item_type="article",
        metadata={
            "authorized_full_feed": True,
            "full_feed_content": "<p>" + " ".join(["strategy"] * 600) + "</p>",
        },
    )

    artifacts = ingest_discovered_articles(source, [item], tmp_path / "data/raw")
    raw_metadata, _ = read_markdown(Path(artifacts[0].raw_path))
    normalized = normalize_raw_artifact(artifacts[0], tmp_path / "data/normalized")

    assert artifacts[0].source_type == "rss_full_content"
    assert "full_feed_content" not in raw_metadata
    assert normalized.primary_content_kind == "full_feed_content"
    assert normalized.selected_fallback == "authorized_full_feed_content"
    assert normalized.quality_status == "usable"


def test_generic_fallback_is_explicit_and_diagnostic() -> None:
    source = Source(id="manual_example", name="Manual Example", lane="manual", type="manual")
    item = DiscoveredItem(source_id=source.id, title="Example", url="https://example.com/article", item_type="article")

    decision = select_html_adapter(source, item)

    assert decision.name == "generic_html_fallback"
    assert decision.metadata["classification_confidence"] == 0.4
    assert decision.metadata["quality_flags"] == ["generic_fallback_used"]
    assert decision.metadata["selected_fallback"] == "generic_html_fallback"
