from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.ingest.discovery import DiscoveredItem
from app.ingest.rss import ingest_discovered_articles, ingest_discovered_podcast_pages
from app.ingest.transcript import TranscriptResult, TranscriptSegment
from app.models import Source


class FakeTranscriptClient:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def transcribe_youtube_url(self, youtube_url: str) -> TranscriptResult:
        self.urls.append(youtube_url)
        return TranscriptResult(
            platform="youtube",
            external_id="t0GiTyz4syY",
            title="Lenny episode",
            source_url=youtube_url,
            permalink="https://www.usetranscribe.io/yt/t0GiTyz4syY/lenny-episode",
            transcript_segments=[TranscriptSegment(start=0.0, end=2.0, text="Useful product point.")],
            summary="Provider summary.",
        )


def test_ingest_discovered_podcast_page_prefers_embedded_youtube_for_usetranscribe(tmp_path, monkeypatch) -> None:
    html = """
<html><body>
  <iframe src="https://www.youtube.com/embed/t0GiTyz4syY"></iframe>
  <h2>Transcript</h2>
  <h3>00:00 - Intro</h3>
  <p>Fallback transcript text.</p>
  <p>More fallback transcript text.</p>
</body></html>
"""

    def fake_get(*args, **kwargs):
        return httpx.Response(200, text=html, request=httpx.Request("GET", str(args[0])))

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(id="lenny_podcast", name="Lenny's Podcast", lane="product_patterns", type="podcast")
    item = DiscoveredItem(
        source_id="lenny_podcast",
        title="Lenny episode",
        url="https://www.lennysnewsletter.com/p/episode",
        item_type="podcast_episode",
        published_at=datetime(2026, 7, 19, tzinfo=UTC),
        metadata={"platform": "rss"},
    )
    client = FakeTranscriptClient()

    artifacts = ingest_discovered_podcast_pages(source, [item], tmp_path, transcript_client=client)  # type: ignore[arg-type]

    assert client.urls == ["https://www.youtube.com/watch?v=t0GiTyz4syY"]
    assert len(artifacts) == 1
    assert artifacts[0].url == "https://www.youtube.com/watch?v=t0GiTyz4syY"
    assert "Useful product point." in Path(artifacts[0].raw_path).read_text()


def test_lenny_newsletter_article_uses_first_party_substack_transcript_before_show_notes(tmp_path, monkeypatch) -> None:
    html = """
<html>
  <body>
    <p>What you'll learn: short show notes.</p>
    <iframe src="https://www.youtube.com/embed/t0GiTyz4syY"></iframe>
    <script>
      {"transcription":{"speaker_map":{"SPEAKER_00":"Claire Vo"},"cdn_url":"https://substackcdn.com/video_upload/post/1/media/transcription.json?Expires=1"}}
    </script>
  </body>
</html>
"""
    transcript_json = {
        "segments": [
            {"start": 0.0, "text": " ".join(["Codex"] * 55), "speaker": "SPEAKER_00"},
        ]
    }

    def fake_get(url, **kwargs):
        request = httpx.Request("GET", str(url))
        if "substackcdn.com" in str(url):
            return httpx.Response(200, json=transcript_json, request=request)
        return httpx.Response(200, text=html, request=request)

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(id="lenny_newsletter", name="Lenny's Newsletter", lane="product_patterns", type="product_newsletter", adapter="rss_or_html")
    item = DiscoveredItem(
        source_id="lenny_newsletter",
        title="Computer and browser use in Codex",
        url="https://www.lennysnewsletter.com/p/computer-and-browser-use-in-codex",
        item_type="article",
        published_at=datetime(2026, 7, 22, tzinfo=UTC),
        metadata={"platform": "rss"},
    )

    artifacts = ingest_discovered_articles(source, [item], tmp_path)

    assert len(artifacts) == 1
    assert artifacts[0].source_type == "podcast_transcript"
    assert artifacts[0].metadata["transcript_provider"] == "substack_media"
    assert artifacts[0].metadata["selected_fallback"] == "substack_transcript_json"
    assert "Claire Vo:" in Path(artifacts[0].raw_path).read_text()
