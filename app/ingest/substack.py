from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import unescape
from pathlib import Path
import json
import re
from typing import Literal

import httpx
from bs4 import BeautifulSoup

from app.ids import content_hash, deterministic_id
from app.models import RawArtifact, Source
from app.store.files import write_markdown
from app.time import now_utc


HTTP_HEADERS = {"User-Agent": "ai-intuition-compiler/0.1 (+substack transcript ingest)"}


@dataclass(frozen=True)
class SubstackTranscriptCandidate:
    url: str
    source_kind: Literal["transcript_json", "captions_vtt"]
    language: str | None = None
    speaker_map: dict[str, str] | None = None


def ingest_substack_transcript_url(
    source: Source,
    url: str,
    raw_root: Path,
    title: str | None = None,
    published_at: datetime | None = None,
) -> RawArtifact:
    response = httpx.get(url, follow_redirects=True, timeout=30, headers=HTTP_HEADERS)
    response.raise_for_status()
    markdown = extract_substack_transcript_markdown(response.text, title=title)
    digest = content_hash(markdown)
    inferred_title = title or _title_from_html(response.text) or url.rstrip("/").split("/")[-1].replace("-", " ").title()
    artifact_id = deterministic_id(source.id, inferred_title, published_at, markdown)
    destination = raw_root / "podcasts" / f"{artifact_id}.md"
    write_markdown(
        destination,
        {
            "source_id": source.id,
            "title": inferred_title,
            "url": url,
            "published_at": published_at.isoformat() if published_at else None,
            "transcript_provider": "substack_page",
            "detected_page_type": "podcast_episode_page",
            "primary_content_kind": "full_transcript",
            "selected_normalizer": "markdown_transcript",
            "classification_confidence": 0.8,
            "classification_signals": ["visible_transcript_section"],
            "quality_status": "usable",
        },
        markdown,
    )
    return RawArtifact(
        id=artifact_id,
        source_id=source.id,
        source_name=source.name,
        lane=source.lane,
        source_type="podcast_transcript",
        title=inferred_title,
        url=url,
        published_at=published_at,
        discovered_at=now_utc(),
        raw_path=str(destination),
        content_hash=digest,
        metadata={
            "transcript_provider": "substack_page",
            "detected_page_type": "podcast_episode_page",
            "primary_content_kind": "full_transcript",
            "selected_normalizer": "markdown_transcript",
            "classification_confidence": 0.8,
            "classification_signals": ["visible_transcript_section"],
            "quality_status": "usable",
        },
    )


def ingest_substack_media_transcript_url(
    source: Source,
    url: str,
    raw_root: Path,
    html: str,
    title: str | None = None,
    published_at: datetime | None = None,
) -> RawArtifact:
    markdown, candidate = extract_substack_media_transcript_markdown(html, title=title)
    digest = content_hash(markdown)
    inferred_title = title or _title_from_html(html) or url.rstrip("/").split("/")[-1].replace("-", " ").title()
    artifact_id = deterministic_id(source.id, inferred_title, published_at, markdown)
    destination = raw_root / "podcasts" / f"{artifact_id}.md"
    metadata = {
        "source_id": source.id,
        "title": inferred_title,
        "url": url,
        "published_at": published_at.isoformat() if published_at else None,
        "transcript_provider": "substack_media",
        "transcript_source": candidate.source_kind,
        "transcript_language": candidate.language,
        "detected_page_type": "podcast_episode_page",
        "primary_content_kind": "full_transcript" if candidate.source_kind == "transcript_json" else "caption_transcript",
        "selected_normalizer": "markdown_transcript",
        "classification_confidence": 0.95,
        "classification_signals": ["substack_media_transcript_metadata", candidate.source_kind],
        "quality_status": "usable",
    }
    write_markdown(destination, metadata, markdown)
    return RawArtifact(
        id=artifact_id,
        source_id=source.id,
        source_name=source.name,
        lane=source.lane,
        source_type="podcast_transcript",
        title=inferred_title,
        url=url,
        published_at=published_at,
        discovered_at=now_utc(),
        raw_path=str(destination),
        content_hash=digest,
        metadata=metadata,
    )


def extract_substack_media_transcript_markdown(html: str, title: str | None = None) -> tuple[str, SubstackTranscriptCandidate]:
    candidates = extract_substack_transcript_candidates(html)
    if not candidates:
        raise ValueError("No Substack media transcript candidates found")
    errors: list[str] = []
    for candidate in candidates:
        try:
            response = httpx.get(candidate.url, follow_redirects=True, timeout=30, headers=HTTP_HEADERS)
            response.raise_for_status()
            if candidate.source_kind == "transcript_json":
                body = _markdown_from_transcript_json(response.json(), title, candidate)
            else:
                body = _markdown_from_vtt(response.text, title, candidate)
            if len(body.split()) < 50:
                raise ValueError("Substack transcript candidate yielded too little text")
            return body, candidate
        except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{candidate.source_kind}: {exc}")
    raise ValueError("; ".join(errors) or "No usable Substack media transcript candidate")


def extract_substack_transcript_candidates(html: str) -> list[SubstackTranscriptCandidate]:
    content = _unescape_embedded_transcript_html(html)
    speaker_map = _extract_speaker_map(content)
    candidates: list[SubstackTranscriptCandidate] = []
    for url in _extract_substack_cdn_urls(content, "transcription.json"):
        candidates.append(SubstackTranscriptCandidate(url=url, source_kind="transcript_json", speaker_map=speaker_map))
    for url in _extract_substack_cdn_urls(content, ".vtt"):
        language = "en" if "/en.vtt" in url else None
        candidates.append(SubstackTranscriptCandidate(url=url, source_kind="captions_vtt", language=language, speaker_map=speaker_map))
    deduped: list[SubstackTranscriptCandidate] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        key = (candidate.url, candidate.source_kind)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def extract_substack_transcript_markdown(html: str, title: str | None = None) -> str:
    soup = BeautifulSoup(_unescape_embedded_transcript_html(html), "html.parser")
    transcript_heading = _find_heading(soup, "Transcript")
    if not transcript_heading:
        raise ValueError("No Transcript section found on Substack page")

    pieces = [f"# {title or _title_from_soup(soup) or 'Podcast Transcript'}", "", "## Transcript", ""]
    for node in transcript_heading.find_all_next(["h2", "h3", "p"]):
        text = node.get_text(" ", strip=True)
        if not text:
            continue
        if node.name == "h2" and text != "Transcript":
            break
        if node.name == "h3":
            pieces.extend([f"### {text}", ""])
        elif node.name == "p":
            pieces.extend([text, ""])
    body = "\n".join(pieces).strip() + "\n"
    if body.count("\n") < 4:
        raise ValueError("Transcript section was found but no transcript text was extracted")
    return body


def extract_youtube_urls_from_substack_html(html: str) -> list[str]:
    content = _unescape_embedded_transcript_html(html)
    video_ids: list[str] = []
    patterns = [
        r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})",
        r"youtube-nocookie\.com/embed/([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        video_ids.extend(re.findall(pattern, content))

    soup = BeautifulSoup(content, "html.parser")
    for node in soup.find_all(["a", "iframe"], href=True):
        video_ids.extend(re.findall(patterns[0], str(node.get("href"))))
    for node in soup.find_all(["iframe"], src=True):
        video_ids.extend(re.findall(patterns[0], str(node.get("src"))))

    urls: list[str] = []
    seen: set[str] = set()
    for video_id in video_ids:
        if video_id in seen:
            continue
        seen.add(video_id)
        urls.append(f"https://www.youtube.com/watch?v={video_id}")
    return urls


def _extract_substack_cdn_urls(content: str, suffix: str) -> list[str]:
    escaped_suffix = re.escape(suffix)
    pattern = rf"https://substackcdn\.com/video_upload/[^\s\"'<>]+?{escaped_suffix}[^\s\"'<>]*"
    urls = []
    for raw in re.findall(pattern, content):
        cleaned = raw.replace("\\u0026", "&").replace("&amp;", "&").rstrip("\\")
        urls.append(cleaned)
    return urls


def _extract_speaker_map(content: str) -> dict[str, str]:
    match = re.search(r'"speaker_map"\s*:\s*(\{.*?\})', content)
    if not match:
        return {}
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    return {str(key): str(value) for key, value in payload.items()}


def _markdown_from_transcript_json(payload: object, title: str | None, candidate: SubstackTranscriptCandidate) -> str:
    segments = _segments_from_transcript_json(payload, candidate.speaker_map or {})
    if not segments:
        raise ValueError("No segments found in Substack transcript JSON")
    return _render_segments(title or "Podcast Transcript", "Substack transcript", segments)


def _segments_from_transcript_json(payload: object, speaker_map: dict[str, str]) -> list[dict[str, object]]:
    raw_segments = _find_segment_list(payload)
    segments: list[dict[str, object]] = []
    for raw in raw_segments:
        if not isinstance(raw, dict):
            continue
        text = raw.get("text") or raw.get("content") or raw.get("word")
        if not text:
            continue
        speaker = raw.get("speaker") or raw.get("speaker_id")
        segments.append(
            {
                "start": _float_or_none(raw.get("start") or raw.get("start_time") or raw.get("timestamp")),
                "text": str(text).strip(),
                "speaker": speaker_map.get(str(speaker), str(speaker)) if speaker else None,
            }
        )
    return segments


def _find_segment_list(payload: object) -> list[object]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("segments", "transcript", "words", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = _find_segment_list(value)
            if nested:
                return nested
    for value in payload.values():
        nested = _find_segment_list(value)
        if nested:
            return nested
    return []


def _markdown_from_vtt(vtt: str, title: str | None, candidate: SubstackTranscriptCandidate) -> str:
    segments = []
    current_start: float | None = None
    current_text: list[str] = []
    for line in vtt.splitlines():
        stripped = line.strip()
        if not stripped or stripped == "WEBVTT" or stripped.isdigit():
            continue
        if "-->" in stripped:
            if current_text:
                segments.append({"start": current_start, "text": " ".join(current_text), "speaker": None})
                current_text = []
            current_start = _seconds_from_vtt_timestamp(stripped.split("-->", 1)[0].strip())
            continue
        current_text.append(re.sub(r"<[^>]+>", "", stripped))
    if current_text:
        segments.append({"start": current_start, "text": " ".join(current_text), "speaker": None})
    if not segments:
        raise ValueError("No cues found in Substack VTT captions")
    return _render_segments(title or "Podcast Transcript", "Substack captions", segments)


def _render_segments(title: str, heading: str, segments: list[dict[str, object]]) -> str:
    pieces = [f"# {title}", "", f"## {heading}", ""]
    for segment in segments:
        timestamp = _format_timestamp(segment.get("start"))
        speaker = segment.get("speaker")
        prefix = f"[{timestamp}] " if timestamp else ""
        if speaker:
            prefix += f"{speaker}: "
        pieces.append(prefix + str(segment["text"]).strip())
        pieces.append("")
    return "\n".join(pieces).strip() + "\n"


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _seconds_from_vtt_timestamp(value: str) -> float | None:
    parts = value.replace(",", ".").split(":")
    try:
        seconds = float(parts[-1])
        minutes = int(parts[-2]) if len(parts) >= 2 else 0
        hours = int(parts[-3]) if len(parts) >= 3 else 0
    except (ValueError, IndexError):
        return None
    return hours * 3600 + minutes * 60 + seconds


def _format_timestamp(value: object) -> str | None:
    seconds = _float_or_none(value)
    if seconds is None:
        return None
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _unescape_embedded_transcript_html(html: str) -> str:
    if "<h2>Transcript</h2>" in html:
        return html
    unescaped = unescape(html).replace('\\"', '"').replace("\\/", "/")
    unescaped = unescaped.replace("\\u0026", "&").replace("\\u003d", "=")
    if "<h2>Transcript</h2>" in unescaped:
        return unescaped
    return unescaped


def _find_heading(soup: BeautifulSoup, text: str):
    for node in soup.find_all(["h1", "h2", "h3", "button", "div", "span"]):
        if node.get_text(" ", strip=True) == text:
            if _has_transcript_body_after(node):
                return node
    return None


def _has_transcript_body_after(node: object) -> bool:
    seen_timestamp_heading = False
    paragraph_count = 0
    for next_node in node.find_all_next(["h2", "h3", "p"], limit=20):
        text = next_node.get_text(" ", strip=True)
        if not text:
            continue
        if next_node.name == "h2" and text != "Transcript":
            if seen_timestamp_heading:
                break
            continue
        if next_node.name == "h3" and any(char.isdigit() for char in text):
            seen_timestamp_heading = True
        if next_node.name == "p" and seen_timestamp_heading:
            paragraph_count += 1
        if paragraph_count >= 2:
            return True
    return False


def _title_from_html(html: str) -> str | None:
    return _title_from_soup(BeautifulSoup(html, "html.parser"))


def _title_from_soup(soup: BeautifulSoup) -> str | None:
    heading = soup.find(["h1", "h2"])
    if heading and heading.get_text(strip=True):
        return heading.get_text(" ", strip=True)
    title = soup.find("title")
    if title and title.get_text(strip=True):
        return title.get_text(" ", strip=True)
    return None
