from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from app.ids import content_hash, deterministic_id
from app.models import RawArtifact, Source
from app.store.files import write_markdown
from app.time import now_utc


BASE_URL = "https://www.usetranscribe.io"
USER_AGENT = "ai-intuition-compiler/0.1 (+repo-first transcript ingestion)"


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float | None
    text: str
    speaker: str | None = None


@dataclass(frozen=True)
class TranscriptResult:
    platform: str
    external_id: str
    title: str
    source_url: str
    permalink: str
    transcript_segments: list[TranscriptSegment]
    summary: str | None = None
    creator: str | None = None
    published_at: datetime | None = None
    duration_seconds: int | None = None
    language: str | None = None
    pipeline_version: str | None = None
    sections: list[dict[str, Any]] | None = None
    chat_pills: list[str] | None = None


def extract_youtube_video_id(url_or_id: str) -> str:
    value = url_or_id.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value
    patterns = [
        r"[?&]v=([A-Za-z0-9_-]{11})",
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"youtube\.com/embed/([A-Za-z0-9_-]{11})",
        r"youtube\.com/shorts/([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract YouTube video id from: {url_or_id}")


def extract_spotify_episode_id(url_or_id: str) -> str:
    value = url_or_id.strip()
    if re.fullmatch(r"[A-Za-z0-9]{22}", value):
        return value
    match = re.search(r"open\.spotify\.com/episode/([A-Za-z0-9]{22})", value)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract Spotify episode id from: {url_or_id}")


def absolutize_permalink(permalink: str) -> str:
    return permalink if permalink.startswith("http") else f"{BASE_URL}{permalink}"


class UseTranscribeClient:
    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(
            base_url=BASE_URL,
            follow_redirects=True,
            timeout=600,
            headers={"User-Agent": USER_AGENT},
        )

    def transcribe_youtube_url(self, youtube_url: str) -> TranscriptResult:
        video_id = extract_youtube_video_id(youtube_url)
        cached = self._check_cached(video_id)
        if cached:
            return self._fetch_cached(cached)
        return self._trigger_transcribe(youtube_url)

    def transcribe_spotify_url(self, spotify_url: str) -> TranscriptResult:
        episode_id = extract_spotify_episode_id(spotify_url)
        response = self.client.get(f"/sp/{episode_id}", params={"format": "json"})
        if response.status_code == 404:
            raise RuntimeError("spotify_not_cached: useTranscribe only serves legacy cached Spotify transcripts and no longer creates new Spotify transcripts.")
        response.raise_for_status()
        return transcript_result_from_cached_json(response.json(), fallback_source_url=spotify_url)

    def transcribe_url(self, url: str) -> TranscriptResult:
        if "spotify.com/episode/" in url or re.fullmatch(r"[A-Za-z0-9]{22}", url.strip()):
            return self.transcribe_spotify_url(url)
        if "youtube.com/" not in url and "youtu.be/" not in url and not re.fullmatch(r"[A-Za-z0-9_-]{11}", url.strip()):
            raise ValueError("useTranscribe only supports YouTube URLs for new transcriptions; Spotify is cached legacy only.")
        return self.transcribe_youtube_url(url)

    def _check_cached(self, video_id: str) -> str | None:
        response = self.client.get("/api/check", params={"platform": "youtube", "id": video_id})
        response.raise_for_status()
        payload = response.json()
        if payload.get("cached"):
            return absolutize_permalink(str(payload["permalink"]))
        return None

    def _fetch_cached(self, permalink: str) -> TranscriptResult:
        response = self.client.get(permalink, params={"format": "json"})
        response.raise_for_status()
        return transcript_result_from_cached_json(response.json())

    def _trigger_transcribe(self, youtube_url: str) -> TranscriptResult:
        with self.client.stream("GET", "/transcribe", params={"url": youtube_url, "summarize": 1}) as stream:
            stream.raise_for_status()
            event: str | None = None
            for line in stream.iter_lines():
                if line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                    continue
                if not line.startswith("data:"):
                    continue
                payload = json.loads(line.split(":", 1)[1].strip())
                if event == "done":
                    return transcript_result_from_sse_done(payload, youtube_url)
                if event == "error":
                    code = payload.get("code", "transcription_failed")
                    message = payload.get("message", "useTranscribe returned an error")
                    raise RuntimeError(f"{code}: {message}")
        raise RuntimeError("useTranscribe stream ended without a done event")


def transcript_result_from_cached_json(payload: dict[str, Any], fallback_source_url: str | None = None) -> TranscriptResult:
    transcript = payload.get("transcript") or {}
    platform = str(payload.get("platform") or "youtube")
    external_id = str(payload["external_id"])
    default_source_url = (
        f"https://www.youtube.com/watch?v={external_id}"
        if platform == "youtube"
        else f"https://open.spotify.com/episode/{external_id}"
    )
    default_permalink = f"/yt/{external_id}" if platform == "youtube" else f"/sp/{external_id}"
    return TranscriptResult(
        platform=platform,
        external_id=external_id,
        title=str(payload.get("title") or external_id),
        source_url=str(payload.get("source_url") or fallback_source_url or default_source_url),
        permalink=absolutize_permalink(str(payload.get("permalink") or default_permalink)),
        transcript_segments=_segments_from_payload(transcript.get("segments") or []),
        summary=payload.get("summary"),
        creator=payload.get("creator"),
        published_at=_parse_datetime(payload.get("published_at")),
        duration_seconds=payload.get("duration_seconds"),
        language=transcript.get("language"),
        pipeline_version=payload.get("pipeline_version"),
        sections=transcript.get("sections"),
        chat_pills=transcript.get("chat_pills"),
    )


def transcript_result_from_sse_done(payload: dict[str, Any], youtube_url: str) -> TranscriptResult:
    metadata = payload.get("metadata") or {}
    video_id = extract_youtube_video_id(youtube_url)
    return TranscriptResult(
        platform="youtube",
        external_id=video_id,
        title=str(metadata.get("title") or video_id),
        source_url=youtube_url,
        permalink=absolutize_permalink(str(payload["permalink"])),
        transcript_segments=_segments_from_payload(payload.get("segments") or []),
        summary=payload.get("summary_md"),
        creator=metadata.get("creator"),
        published_at=_parse_datetime(metadata.get("published_at")),
        duration_seconds=metadata.get("duration_seconds"),
        language=payload.get("language"),
        pipeline_version=payload.get("source"),
        sections=payload.get("sections"),
        chat_pills=payload.get("chat_pills"),
    )


def write_transcript_raw_artifact(result: TranscriptResult, source: Source, raw_root: Path) -> RawArtifact:
    body = render_transcript_markdown(result)
    digest = content_hash(body)
    artifact_id = deterministic_id(source.id, result.title, result.published_at, body)
    destination = raw_root / "podcasts" / f"{artifact_id}.md"
    write_markdown(
        destination,
        {
            "source_id": source.id,
            "title": result.title,
            "url": result.source_url,
            "published_at": result.published_at.isoformat() if result.published_at else None,
            "transcript_permalink": result.permalink,
            "creator": result.creator,
            "duration_seconds": result.duration_seconds,
            "language": result.language,
            "pipeline_version": result.pipeline_version,
            "sections": result.sections,
            "chat_pills": result.chat_pills,
        },
        body,
    )
    return RawArtifact(
        id=artifact_id,
        source_id=source.id,
        source_name=source.name,
        lane=source.lane,
        source_type="podcast_transcript",
        title=result.title,
        url=result.source_url,
        author=result.creator,
        published_at=result.published_at,
        discovered_at=now_utc(),
        raw_path=str(destination),
        content_hash=digest,
        metadata={
            "transcript_permalink": result.permalink,
            "duration_seconds": result.duration_seconds,
            "language": result.language,
            "pipeline_version": result.pipeline_version,
            "sections": result.sections,
            "chat_pills": result.chat_pills,
        },
    )


def render_transcript_markdown(result: TranscriptResult) -> str:
    lines = [f"# {result.title}", ""]
    if result.summary:
        lines.extend(["## Provider summary", "", result.summary.strip(), ""])
    lines.extend(["## Transcript", ""])
    for segment in result.transcript_segments:
        timestamp = _format_timestamp(segment.start)
        speaker = f"{segment.speaker}: " if segment.speaker else ""
        lines.append(f"[{timestamp}] {speaker}{segment.text.strip()}")
    return "\n".join(lines).strip() + "\n"


def _segments_from_payload(segments: list[dict[str, Any]]) -> list[TranscriptSegment]:
    return [
        TranscriptSegment(
            start=float(segment.get("start") or 0.0),
            end=float(segment["end"]) if segment.get("end") is not None else None,
            text=str(segment.get("text") or ""),
            speaker=segment.get("speaker"),
        )
        for segment in segments
        if segment.get("text")
    ]


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _format_timestamp(seconds: float) -> str:
    total = int(seconds)
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
