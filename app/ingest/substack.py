from __future__ import annotations

from datetime import datetime
from html import unescape
from pathlib import Path
import re

import httpx
from bs4 import BeautifulSoup

from app.ids import content_hash, deterministic_id
from app.models import RawArtifact, Source
from app.store.files import write_markdown
from app.time import now_utc


def ingest_substack_transcript_url(
    source: Source,
    url: str,
    raw_root: Path,
    title: str | None = None,
    published_at: datetime | None = None,
) -> RawArtifact:
    response = httpx.get(url, follow_redirects=True, timeout=30)
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
        metadata={"transcript_provider": "substack_page"},
    )


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


def _unescape_embedded_transcript_html(html: str) -> str:
    if "<h2>Transcript</h2>" in html:
        return html
    unescaped = unescape(html).replace('\\"', '"').replace("\\/", "/")
    if "<h2>Transcript</h2>" in unescaped:
        return unescaped
    return html


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
