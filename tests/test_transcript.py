from app.ingest.transcript import (
    UseTranscribeClient,
    absolutize_permalink,
    extract_spotify_episode_id,
    extract_youtube_video_id,
    render_transcript_markdown,
    transcript_result_from_cached_json,
    transcript_result_from_sse_done,
)


def test_extract_youtube_video_id_from_common_shapes() -> None:
    assert extract_youtube_video_id("DULfEcPR0Gc") == "DULfEcPR0Gc"
    assert extract_youtube_video_id("https://www.youtube.com/watch?v=DULfEcPR0Gc") == "DULfEcPR0Gc"
    assert extract_youtube_video_id("https://youtu.be/DULfEcPR0Gc?t=12") == "DULfEcPR0Gc"
    assert extract_youtube_video_id("https://www.youtube.com/embed/DULfEcPR0Gc") == "DULfEcPR0Gc"


def test_extract_spotify_episode_id_from_common_shapes() -> None:
    episode_id = "4cOdK2wGLETKBW3PvgPWqT"
    assert extract_spotify_episode_id(episode_id) == episode_id
    assert extract_spotify_episode_id(f"https://open.spotify.com/episode/{episode_id}") == episode_id
    assert extract_spotify_episode_id(f"https://open.spotify.com/episode/{episode_id}?si=abc") == episode_id


def test_absolutize_permalink_handles_path_and_url() -> None:
    assert absolutize_permalink("/yt/DULfEcPR0Gc/title") == "https://www.usetranscribe.io/yt/DULfEcPR0Gc/title"
    assert absolutize_permalink("https://www.usetranscribe.io/yt/DULfEcPR0Gc/title") == "https://www.usetranscribe.io/yt/DULfEcPR0Gc/title"


def test_cached_json_shape_parses_nested_segments() -> None:
    result = transcript_result_from_cached_json(
        {
            "platform": "youtube",
            "external_id": "DULfEcPR0Gc",
            "permalink": "/yt/DULfEcPR0Gc/title",
            "title": "AI agents explained",
            "creator": "Example",
            "duration_seconds": 60,
            "source_url": "https://www.youtube.com/watch?v=DULfEcPR0Gc",
            "transcript": {
                "language": "en",
                "segments": [
                    {"start": 0.0, "end": 4.2, "text": "Hello"},
                    {"start": 4.2, "end": 8.6, "text": "World", "speaker": "Speaker 1"},
                ],
                "sections": [
                    {
                        "start": 0.0,
                        "title": "Opening",
                        "question": "What is this about?",
                        "answer": "Agents.",
                        "takeaways": ["Loops matter."],
                    }
                ],
                "chat_pills": ["What are the action items?"],
            },
            "summary": "## TL;DR\nSummary.",
            "pipeline_version": "v1",
        }
    )

    assert result.title == "AI agents explained"
    assert result.permalink == "https://www.usetranscribe.io/yt/DULfEcPR0Gc/title"
    assert len(result.transcript_segments) == 2
    assert result.transcript_segments[1].speaker == "Speaker 1"
    assert result.summary == "## TL;DR\nSummary."
    assert result.sections == [
        {
            "start": 0.0,
            "title": "Opening",
            "question": "What is this about?",
            "answer": "Agents.",
            "takeaways": ["Loops matter."],
        }
    ]
    assert result.chat_pills == ["What are the action items?"]


def test_cached_spotify_json_shape_uses_sp_permalink_and_source_url() -> None:
    episode_id = "4cOdK2wGLETKBW3PvgPWqT"
    result = transcript_result_from_cached_json(
        {
            "platform": "spotify",
            "external_id": episode_id,
            "title": "Podcast episode",
            "transcript": {"segments": [{"start": 0.0, "end": 4.2, "text": "Hello"}]},
            "summary": "Summary.",
        }
    )

    assert result.platform == "spotify"
    assert result.source_url == f"https://open.spotify.com/episode/{episode_id}"
    assert result.permalink == f"https://www.usetranscribe.io/sp/{episode_id}"


def test_sse_done_shape_parses_top_level_segments() -> None:
    result = transcript_result_from_sse_done(
        {
            "permalink": "https://www.usetranscribe.io/yt/DULfEcPR0Gc/title",
            "segments": [{"start": 0.0, "end": 4.2, "text": "Hello"}],
            "sections": [{"start": 0.0, "title": "Opening"}],
            "chat_pills": ["What changed?"],
            "summary_md": "Summary.",
            "metadata": {"title": "AI agents explained", "duration_seconds": 60},
            "language": "en",
            "source": "captions",
        },
        "https://www.youtube.com/watch?v=DULfEcPR0Gc",
    )

    assert result.external_id == "DULfEcPR0Gc"
    assert result.title == "AI agents explained"
    assert result.summary == "Summary."
    assert result.pipeline_version == "captions"
    assert result.sections == [{"start": 0.0, "title": "Opening"}]
    assert result.chat_pills == ["What changed?"]


def test_render_transcript_markdown_includes_summary_and_timestamps() -> None:
    result = transcript_result_from_cached_json(
        {
            "platform": "youtube",
            "external_id": "DULfEcPR0Gc",
            "title": "AI agents explained",
            "source_url": "https://www.youtube.com/watch?v=DULfEcPR0Gc",
            "transcript": {"segments": [{"start": 65.0, "end": 70.0, "text": "Useful point"}]},
            "summary": "Summary.",
        }
    )

    markdown = render_transcript_markdown(result)

    assert "# AI agents explained" in markdown
    assert "## Provider summary" in markdown
    assert "[1:05] Useful point" in markdown


def test_transcribe_url_rejects_non_youtube_non_legacy_spotify_url() -> None:
    client = UseTranscribeClient()

    try:
        client.transcribe_url("https://example.com/audio.mp3")
    except ValueError as exc:
        assert "only supports YouTube" in str(exc)
    else:
        raise AssertionError("Expected non-YouTube URLs to be rejected before useTranscribe")
