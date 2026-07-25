from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.ingest.discovery import (
    DateWindow,
    classify_source_health,
    discover_html_index,
    discover_openai_research_rss,
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


def test_authorized_rss_discovery_preserves_full_feed_content(monkeypatch) -> None:
    rss = """
<rss><channel><item>
  <title>Full strategy article</title>
  <link>https://stratechery.com/2026/full-article</link>
  <pubDate>Mon, 25 May 2026 12:00:00 GMT</pubDate>
  <content:encoded xmlns:content="http://purl.org/rss/1.0/modules/content/"><![CDATA[<p>Full article body.</p>]]></content:encoded>
</item></channel></rss>
"""

    def fake_get(*args, **kwargs):
        return httpx.Response(200, text=rss, request=httpx.Request("GET", str(args[0])))

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(
        id="stratechery",
        name="Stratechery",
        lane="strategy_value_capture",
        type="strategy_newsletter",
        adapter="rss_or_html",
        rss_url="https://stratechery.com/feed/",
        rss_url_env="STRATECHERY_PERSONAL_RSS_URL",
        urls=["https://private.example.com/feed"],
    )

    items = discover_rss_or_html(source, DateWindow())

    assert items[0].metadata["authorized_full_feed"] is True
    assert items[0].metadata["full_feed_content"] == "<p>Full article body.</p>"


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


def test_openai_research_rss_filters_first_party_research_category(monkeypatch) -> None:
    rss = """
<rss><channel>
  <item><title>Research evaluation</title><link>https://openai.com/index/research-evaluation</link><pubDate>Wed, 08 Jul 2026 13:00:00 GMT</pubDate><category>Research</category></item>
  <item><title>Product launch</title><link>https://openai.com/index/product-launch</link><pubDate>Wed, 08 Jul 2026 13:00:00 GMT</pubDate><category>Product</category></item>
  <item><title>Undated research</title><link>https://openai.com/index/undated-research</link><category>Research</category></item>
</channel></rss>
"""

    def fake_get(url, **kwargs):
        assert str(url) == "https://openai.com/news/rss.xml"
        return httpx.Response(200, text=rss, request=httpx.Request("GET", str(url)))

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(
        id="openai_research",
        name="OpenAI Research",
        lane="frontier_primitives",
        type="lab_research",
        adapter="openai_research_rss",
        rss_url="https://openai.com/news/rss.xml",
    )

    items = discover_openai_research_rss(source, DateWindow())

    assert [item.title for item in items] == ["Research evaluation"]
    assert items[0].published_at == datetime(2026, 7, 8, 13, tzinfo=UTC)
    assert items[0].metadata["entry_categories"] == ["Research"]
    assert items[0].metadata["category_filter"] == "Research"


def test_openai_research_rss_rejects_malformed_payload(monkeypatch) -> None:
    def fake_get(url, **kwargs):
        return httpx.Response(200, text="<rss><channel><item>", request=httpx.Request("GET", str(url)))

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(
        id="openai_research",
        name="OpenAI Research",
        lane="frontier_primitives",
        type="lab_research",
        adapter="openai_research_rss",
        rss_url="https://openai.com/news/rss.xml",
    )

    with pytest.raises(Exception, match="malformed"):
        discover_openai_research_rss(source, DateWindow())


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


def test_google_deepmind_discovery_enriches_missing_dates_from_article_jsonld(monkeypatch) -> None:
    index_html = """
<html><body>
  <a href="/blog/our-approach-to-bioresilience/">Our approach to bioresilience</a>
</body></html>
"""
    article_html = """
<html><head>
  <script type="application/ld+json">
    {"@type": "BlogPosting", "datePublished": "2026-07-16T00:00:00Z"}
  </script>
</head><body><h1>Our approach to bioresilience</h1></body></html>
"""

    def fake_get(url, **kwargs):
        request = httpx.Request("GET", str(url))
        if str(url).rstrip("/") == "https://deepmind.google/blog":
            return httpx.Response(200, text=index_html, request=request)
        return httpx.Response(200, text=article_html, request=request)

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(
        id="google_deepmind_blog",
        name="Google DeepMind Blog",
        lane="frontier_primitives",
        type="x",
        adapter="html_index",
        urls=["https://deepmind.google/blog"],
    )

    items = discover_html_index(source, DateWindow())

    assert len(items) == 1
    assert items[0].published_at == datetime(2026, 7, 16, tzinfo=UTC)
    assert items[0].metadata["date_enrichment_status"] == "success"
    assert items[0].metadata["date_enriched_via"] == "json_ld"


def test_date_enrichment_considers_more_than_limit_before_window_filtering(monkeypatch) -> None:
    index_html = """
<html><body>
  <a href="/blog/old-breakthrough/">Old breakthrough</a>
  <a href="/blog/fresh-update/">Fresh update</a>
</body></html>
"""
    article_dates = {
        "https://deepmind.google/blog/old-breakthrough/": "2026-01-01T00:00:00Z",
        "https://deepmind.google/blog/fresh-update/": "2026-07-22T00:00:00Z",
    }

    def fake_get(url, **kwargs):
        request = httpx.Request("GET", str(url))
        if str(url).rstrip("/") == "https://deepmind.google/blog":
            return httpx.Response(200, text=index_html, request=request)
        date = article_dates[str(url)]
        return httpx.Response(
            200,
            text=f'<html><head><meta property="article:published_time" content="{date}"></head></html>',
            request=request,
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(
        id="google_deepmind_blog",
        name="Google DeepMind Blog",
        lane="frontier_primitives",
        type="x",
        adapter="html_index",
        urls=["https://deepmind.google/blog"],
    )

    items = discover_html_index(
        source,
        DateWindow(start=datetime(2026, 7, 20, tzinfo=UTC), end=datetime(2026, 7, 26, tzinfo=UTC)),
        limit=1,
    )

    assert len(items) == 1
    assert items[0].title == "Fresh update"
    assert items[0].published_at == datetime(2026, 7, 22, tzinfo=UTC)


def test_anthropic_engineering_discovery_enriches_featured_article_date_from_visible_text(monkeypatch) -> None:
    index_html = """
<html><body>
  <a href="/engineering/how-we-contain-claude">Featured How we contain Claude across products</a>
</body></html>
"""
    article_html = """
<html><body>
  <h1>How we contain Claude across products</h1>
  <p>Published May 25, 2026</p>
</body></html>
"""

    def fake_get(url, **kwargs):
        request = httpx.Request("GET", str(url))
        if str(url).rstrip("/") == "https://www.anthropic.com/engineering":
            return httpx.Response(200, text=index_html, request=request)
        return httpx.Response(200, text=article_html, request=request)

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(
        id="anthropic_engineering",
        name="Anthropic Engineering",
        lane="product_patterns",
        type="x",
        adapter="html_index",
        urls=["https://www.anthropic.com/engineering"],
    )

    items = discover_html_index(source, DateWindow())

    assert len(items) == 1
    assert items[0].published_at == datetime(2026, 5, 25, tzinfo=UTC)
    assert items[0].metadata["date_enrichment_status"] == "success"
    assert items[0].metadata["date_enriched_via"] == "visible_text"


def test_alignment_science_discovery_records_date_enrichment_miss(monkeypatch) -> None:
    index_html = """
<html><body>
  <a href="2026/agentic-misalignment-summer-2026/">Agentic Misalignment in Summer 2026 We present four case studies.</a>
</body></html>
"""
    article_html = "<html><body><h1>Agentic Misalignment in Summer 2026</h1><p>No publish date exposed.</p></body></html>"

    def fake_get(url, **kwargs):
        request = httpx.Request("GET", str(url))
        if str(url).rstrip("/") == "https://alignment.anthropic.com":
            return httpx.Response(200, text=index_html, request=request)
        return httpx.Response(200, text=article_html, request=request)

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(
        id="anthropic_alignment_science",
        name="Anthropic Alignment Science",
        lane="reliability_failures",
        type="x",
        adapter="html_index",
        urls=["https://alignment.anthropic.com"],
    )

    items = discover_html_index(source, DateWindow())

    assert len(items) == 1
    assert items[0].published_at is None
    assert items[0].metadata["date_enrichment_status"] == "no_date_found"
    assert items[0].metadata["date_enrichment_checked_url"] == "https://alignment.anthropic.com/2026/agentic-misalignment-summer-2026/"


def test_frontier_red_team_redirected_index_uses_final_url_and_reports_quiet_health(monkeypatch) -> None:
    html = """
<html><body>
  <a href="/research/project-pilot">Jul 24, 2026 Frontier Red Team Project Pilot: Can AI control a drone?</a>
</body></html>
"""

    def fake_get(url, **kwargs):
        request = httpx.Request("GET", "https://www.anthropic.com/research/team/frontier-red-team")
        return httpx.Response(200, text=html, request=request)

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(
        id="anthropic_frontier_red_team",
        name="Anthropic Frontier Red Team",
        lane="reliability_failures",
        type="x",
        adapter="html_index",
        urls=["https://red.anthropic.com/"],
    )

    items = discover_html_index(source, DateWindow())

    assert len(items) == 1
    assert items[0].url == "https://www.anthropic.com/research/project-pilot"
    assert items[0].published_at == datetime(2026, 7, 24, tzinfo=UTC)
    assert classify_source_health(source, items) == "healthy"
    assert classify_source_health(source, []) == "needs_source_path_review"


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
