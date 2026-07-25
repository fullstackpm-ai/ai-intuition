from pathlib import Path

import httpx

from app.ingest.substack import (
    extract_substack_transcript_candidates,
    extract_substack_transcript_markdown,
    extract_youtube_urls_from_substack_html,
    ingest_substack_media_transcript_url,
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


def test_extract_substack_transcript_candidates_prefers_transcript_json_before_vtt() -> None:
    html = """
<html><body><script>
{"transcription":{"speaker_map":{"SPEAKER_00":"Claire Vo"},"cdn_url":"https://substackcdn.com/video_upload/post/1/media/transcription.json?Expires=1","signed_captions":[{"language":"en","url":"https://substackcdn.com/video_upload/post/1/media/en.vtt?Expires=1"}]}}
</script></body></html>
"""

    candidates = extract_substack_transcript_candidates(html)

    assert [candidate.source_kind for candidate in candidates] == ["transcript_json", "captions_vtt"]
    assert candidates[0].speaker_map == {"SPEAKER_00": "Claire Vo"}


def test_ingest_substack_media_transcript_url_writes_first_party_transcript(tmp_path, monkeypatch) -> None:
    html = """
<html>
  <head><title>Computer and browser use in Codex</title></head>
  <body><script>
  {"transcription":{"speaker_map":{"SPEAKER_00":"Claire Vo"},"cdn_url":"https://substackcdn.com/video_upload/post/1/media/transcription.json?Expires=1"}}
  </script></body>
</html>
"""
    transcript_words = " ".join(["agent"] * 60)
    transcript_json = {
        "segments": [
            {"start": 0.0, "text": f"{transcript_words} loop harness.", "speaker": "SPEAKER_00"},
        ]
    }

    def fake_get(url, **kwargs):
        return httpx.Response(200, json=transcript_json, request=httpx.Request("GET", str(url)))

    monkeypatch.setattr(httpx, "get", fake_get)
    source = Source(id="lenny_newsletter", name="Lenny's Newsletter", lane="product_patterns", type="product_newsletter")

    artifact = ingest_substack_media_transcript_url(
        source,
        "https://www.lennysnewsletter.com/p/computer-and-browser-use-in-codex",
        tmp_path,
        html,
        title="Computer and browser use in Codex",
    )

    body = Path(artifact.raw_path).read_text()
    assert artifact.source_type == "podcast_transcript"
    assert artifact.metadata["transcript_provider"] == "substack_media"
    assert artifact.metadata["primary_content_kind"] == "full_transcript"
    assert "Claire Vo:" in body
    assert "loop harness" in body


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
