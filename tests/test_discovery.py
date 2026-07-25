from datetime import UTC, datetime, timedelta

import httpx

from app.ingest.discovery import (
    DateWindow,
    discover_html_index,
    discover_podcast_page_or_youtube,
    discover_rss_or_html,
)
from app.models import Source


def test_rss_discovery_filters_by_window(monkeypatch) -> None:
    rss = """
<rss><channel>
  <item>
    <title>Fresh article</title>
    <link>https://example.com/blog/fresh</link>
    <pubDate>Mon, 25 May 2026 12:00:00 GMT</pubDate>
  </item>
  <item>
    <title>Old article</title>
    <link>https://example.com/blog/old</link>
    <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
  </item>
</channel></rss>
"""

    def fake_get(*args, **kwargs):
        return httpx.Response(200, text=rss, request=httpx.Request("GET", str(args[0])))

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(id="example", name="Example", lane="frontier_primitives", type="x", adapter="rss_or_html", urls=["https://example.com/feed"])

    items = discover_rss_or_html(
        source,
        DateWindow(start=datetime(2026, 5, 24, tzinfo=UTC), end=datetime(2026, 5, 26, tzinfo=UTC)),
    )

    assert [item.title for item in items] == ["Fresh article"]


def test_html_index_discovery_keeps_article_links(monkeypatch) -> None:
    html = """
<html><body>
  <a href="/research/agent-loop">Agent Loop</a>
  <a href="/research">Research index</a>
  <a href="https://other.example.com/research/nope">External</a>
</body></html>
"""

    def fake_get(*args, **kwargs):
        return httpx.Response(200, text=html, request=httpx.Request("GET", str(args[0])))

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(id="example", name="Example", lane="frontier_primitives", type="x", adapter="html_index", urls=["https://example.com/research"])

    items = discover_html_index(source, DateWindow())

    assert len(items) == 1
    assert items[0].title == "Agent Loop"
    assert items[0].url == "https://example.com/research/agent-loop"


def test_openai_research_discovery_keeps_only_research_cards_with_dates(monkeypatch) -> None:
    html = """
<html><body>
  <a href="/index/gpt-red/">GPT-Red: Unlocking Self-Improvement for Robustness Safety Jul 15, 2026</a>
  <a href="/index/separating-signal-from-noise/">Separating signal from noise in coding evaluations Research Jul 8, 2026</a>
  <a href="/research/index/">Research Index</a>
</body></html>
"""

    def fake_get(*args, **kwargs):
        return httpx.Response(200, text=html, request=httpx.Request("GET", str(args[0])))

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(id="openai_research", name="OpenAI Research", lane="frontier_primitives", type="x", adapter="html_index", urls=["https://openai.com/news/research/"])

    items = discover_html_index(source, DateWindow())

    assert len(items) == 1
    assert items[0].title == "Separating signal from noise in coding evaluations"
    assert items[0].url == "https://openai.com/index/separating-signal-from-noise/"
    assert items[0].published_at == datetime(2026, 7, 8, tzinfo=UTC)


def test_anthropic_research_discovery_filters_team_pages_and_extracts_dates(monkeypatch) -> None:
    html = """
<html><body>
  <a href="/research/team/alignment">Alignment</a>
  <a href="/research/project-pilot">Jul 24, 2026 Frontier Red Team Project Pilot: Can AI control a drone?</a>
</body></html>
"""

    def fake_get(*args, **kwargs):
        return httpx.Response(200, text=html, request=httpx.Request("GET", str(args[0])))

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(id="anthropic_research", name="Anthropic Research", lane="reliability_failures", type="x", adapter="html_index", urls=["https://www.anthropic.com/research"])

    items = discover_html_index(source, DateWindow())

    assert len(items) == 1
    assert items[0].title == "Project Pilot: Can AI control a drone?"
    assert items[0].url == "https://www.anthropic.com/research/project-pilot"
    assert items[0].published_at == datetime(2026, 7, 24, tzinfo=UTC)


def test_google_blog_discovery_filters_archive_and_non_blog_pages(monkeypatch) -> None:
    html = """
<html><body>
  <a href="/blog/rss/">Rss</a>
  <a href="/blog/2026">2026</a>
  <a href="/blog/label/algorithms-theory">Algorithms & Theory</a>
  <a href="javascript(0):void">Javascript(0):Void</a>
  <a href="/research/evals/">Evals</a>
  <a href="/blog/symptomai-towards-a-conversational-ai-agent/">July 22, 2026 SymptomAI: Towards a conversational AI agent General Science · Natural Language Processing</a>
</body></html>
"""

    def fake_get(*args, **kwargs):
        return httpx.Response(200, text=html, request=httpx.Request("GET", str(args[0])))

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(id="google_research_blog", name="Google Research Blog", lane="frontier_primitives", type="x", adapter="html_index", urls=["https://research.google/blog/"])

    items = discover_html_index(source, DateWindow())

    assert len(items) == 1
    assert items[0].title == "SymptomAI: Towards a conversational AI agent General Science · Natural Language Processing"
    assert items[0].url == "https://research.google/blog/symptomai-towards-a-conversational-ai-agent/"
    assert items[0].published_at == datetime(2026, 7, 22, tzinfo=UTC)


def test_alignment_science_discovery_allows_year_slug_posts(monkeypatch) -> None:
    html = """
<html><body>
  <a href="2026/agentic-misalignment-summer-2026/">Agentic Misalignment in Summer 2026 We present four case studies.</a>
  <a href="2025/">2025</a>
</body></html>
"""

    def fake_get(*args, **kwargs):
        return httpx.Response(200, text=html, request=httpx.Request("GET", str(args[0])))

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(id="anthropic_alignment_science", name="Anthropic Alignment Science", lane="reliability_failures", type="x", adapter="html_index", urls=["https://alignment.anthropic.com/"])

    items = discover_html_index(source, DateWindow())

    assert len(items) == 1
    assert items[0].title == "Agentic Misalignment in Summer 2026 We present four case studies."
    assert items[0].url == "https://alignment.anthropic.com/2026/agentic-misalignment-summer-2026/"


def test_podcast_discovery_finds_youtube_links(monkeypatch) -> None:
    html = """
<html><body>
  <a href="https://www.youtube.com/watch?v=DULfEcPR0Gc">Episode</a>
  <a href="https://youtu.be/AAAAAAAAAAA">Short link</a>
</body></html>
"""

    def fake_get(*args, **kwargs):
        return httpx.Response(200, text=html, request=httpx.Request("GET", str(args[0])))

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(id="pod", name="Podcast", lane="frontier_priors", type="podcast", adapter="podcast_episode_page_or_youtube", urls=["https://example.com/podcast"])

    items = discover_podcast_page_or_youtube(source, DateWindow())

    assert [item.url for item in items] == [
        "https://www.youtube.com/watch?v=DULfEcPR0Gc",
        "https://youtu.be/AAAAAAAAAAA",
    ]
    assert all(item.item_type == "video" for item in items)


def test_podcast_discovery_reads_rss_episode_entries(monkeypatch) -> None:
    rss = """
<rss><channel>
  <item>
    <title>Fresh episode</title>
    <link>https://example.com/p/fresh-episode</link>
    <pubDate>Mon, 25 May 2026 12:00:00 GMT</pubDate>
    <enclosure url="https://media.example.com/fresh.mp3" type="audio/mpeg" />
  </item>
</channel></rss>
"""

    def fake_get(*args, **kwargs):
        return httpx.Response(200, text=rss, request=httpx.Request("GET", str(args[0])))

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(id="pod", name="Podcast", lane="frontier_priors", type="podcast", adapter="podcast_episode_page_or_youtube", urls=["https://example.com/feed"])

    items = discover_podcast_page_or_youtube(
        source,
        DateWindow(start=datetime(2026, 5, 24, tzinfo=UTC), end=datetime(2026, 5, 26, tzinfo=UTC)),
    )

    assert len(items) == 1
    assert items[0].title == "Fresh episode"
    assert items[0].item_type == "podcast_episode"
    assert items[0].metadata["platform"] == "rss"
    assert items[0].metadata["audio_url"] == "https://media.example.com/fresh.mp3"


def test_podcast_discovery_finds_spotify_episode_links(monkeypatch) -> None:
    html = """
<html><body>
  <a href="https://open.spotify.com/episode/4cOdK2wGLETKBW3PvgPWqT">Spotify episode</a>
</body></html>
"""

    def fake_get(*args, **kwargs):
        return httpx.Response(200, text=html, request=httpx.Request("GET", str(args[0])))

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(id="pod", name="Podcast", lane="frontier_priors", type="podcast", adapter="podcast_episode_page_or_youtube", urls=["https://example.com/podcast"])

    items = discover_podcast_page_or_youtube(source, DateWindow())

    assert len(items) == 1
    assert items[0].url == "https://open.spotify.com/episode/4cOdK2wGLETKBW3PvgPWqT"
    assert items[0].item_type == "podcast_episode"


def test_date_window_keeps_undated_items() -> None:
    window = DateWindow(start=datetime.now(UTC) - timedelta(days=7), end=datetime.now(UTC))

    assert window.contains(None)
