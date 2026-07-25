from pathlib import Path

import httpx

from app.ingest.substack import (
    extract_substack_transcript_markdown,
    extract_youtube_urls_from_substack_html,
    ingest_substack_transcript_url,
)
from app.models import Source


HTML = """
<html>
  <head><title>Eric Jang - Building AlphaGo from scratch</title></head>
  <body>
    <h1>Eric Jang - Building AlphaGo from scratch</h1>
    <p>Intro copy.</p>
    <h2>Transcript</h2>
    <h3>00:00:00 - Opening</h3>
    <p>Dwarkesh Patel</p>
    <p>Welcome back.</p>
    <h3>00:01:00 - Response</h3>
    <p>Eric Jang</p>
    <p>Thanks for having me.</p>
    <h2>Comments</h2>
    <p>This should not be included.</p>
  </body>
</html>
"""


def test_extract_substack_transcript_markdown_stops_at_next_section() -> None:
    markdown = extract_substack_transcript_markdown(HTML)

    assert "# Eric Jang - Building AlphaGo from scratch" in markdown
    assert "### 00:00:00 - Opening" in markdown
    assert "Dwarkesh Patel" in markdown
    assert "Welcome back." in markdown
    assert "This should not be included." not in markdown


def test_extract_youtube_urls_from_substack_html_dedupes_embeds() -> None:
    html = """
<html><body>
  <iframe src="https://www.youtube.com/embed/t0GiTyz4syY"></iframe>
  <a href="https://youtu.be/t0GiTyz4syY">Watch</a>
  <a href="https://www.youtube.com/watch?v=DULfEcPR0Gc">Second video</a>
</body></html>
"""

    assert extract_youtube_urls_from_substack_html(html) == [
        "https://www.youtube.com/watch?v=t0GiTyz4syY",
        "https://www.youtube.com/watch?v=DULfEcPR0Gc",
    ]


def test_ingest_substack_transcript_url_writes_raw_artifact(tmp_path, monkeypatch) -> None:
    def fake_get(*args, **kwargs):
        return httpx.Response(200, text=HTML, request=httpx.Request("GET", str(args[0])))

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(id="dwarkesh_podcast", name="Dwarkesh Podcast", lane="frontier_priors", type="podcast")

    artifact = ingest_substack_transcript_url(
        source,
        "https://www.dwarkesh.com/p/eric-jang",
        tmp_path,
        title="Eric Jang - Building AlphaGo from scratch",
    )

    assert artifact.source_type == "podcast_transcript"
    assert artifact.metadata["transcript_provider"] == "substack_page"
    assert "dwarkesh_podcast" in artifact.id
    assert "Welcome back." in Path(artifact.raw_path).read_text()
