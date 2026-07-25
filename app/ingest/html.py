from __future__ import annotations

from datetime import datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from app.ids import content_hash, deterministic_id
from app.models import RawArtifact, Source
from app.store.files import write_markdown
from app.time import now_utc


HTTP_HEADERS = {"User-Agent": "ai-intuition-compiler/0.1 (+article ingest)"}


def fetch_html(url: str) -> str:
    response = httpx.get(url, follow_redirects=True, timeout=20, headers=HTTP_HEADERS)
    response.raise_for_status()
    return response.text


def ingest_html_url(
    source: Source,
    url: str,
    raw_root: Path,
    title: str | None = None,
    published_at: datetime | None = None,
    metadata: dict[str, object] | None = None,
) -> RawArtifact:
    html = fetch_html(url)
    return write_html_raw_artifact(source, url, html, raw_root, title=title, published_at=published_at, metadata=metadata)


def write_html_raw_artifact(
    source: Source,
    url: str,
    html: str,
    raw_root: Path,
    title: str | None = None,
    published_at: datetime | None = None,
    metadata: dict[str, object] | None = None,
) -> RawArtifact:
    inferred_title = title or url.rstrip("/").split("/")[-1].replace("-", " ").title() or source.name
    digest = content_hash(html)
    artifact_id = deterministic_id(source.id, inferred_title, published_at, html)
    destination = raw_root / "lab-posts" / f"{artifact_id}.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html)
    return RawArtifact(
        id=artifact_id,
        source_id=source.id,
        source_name=source.name,
        lane=source.lane,
        source_type="html",
        title=inferred_title,
        url=url,
        published_at=published_at,
        discovered_at=now_utc(),
        raw_path=str(destination),
        content_hash=digest,
        metadata=metadata or {},
    )


def write_markdown_raw_artifact(
    source: Source,
    url: str,
    body: str,
    raw_root: Path,
    title: str,
    published_at: datetime | None = None,
    metadata: dict[str, object] | None = None,
) -> RawArtifact:
    """Persist authorized feed content without refetching a potentially paywalled page."""
    markdown_body = _feed_html_to_markdown(body)
    digest = content_hash(markdown_body)
    artifact_id = deterministic_id(source.id, title, published_at, markdown_body)
    destination = raw_root / "strategy" / f"{artifact_id}.md"
    raw_metadata = {
        "source_id": source.id,
        "title": title,
        "url": url,
        "published_at": published_at.isoformat() if published_at else None,
        **(metadata or {}),
    }
    write_markdown(destination, raw_metadata, markdown_body)
    return RawArtifact(
        id=artifact_id,
        source_id=source.id,
        source_name=source.name,
        lane=source.lane,
        source_type="rss_full_content",
        title=title,
        url=url,
        published_at=published_at,
        discovered_at=now_utc(),
        raw_path=str(destination),
        content_hash=digest,
        metadata=raw_metadata,
    )


def _feed_html_to_markdown(body: str) -> str:
    soup = BeautifulSoup(body, "html.parser")
    blocks = [
        node.get_text(" ", strip=True)
        for node in soup.find_all(["h1", "h2", "h3", "p", "li", "blockquote"])
        if node.get_text(" ", strip=True)
    ]
    return "\n\n".join(blocks) if blocks else soup.get_text(" ", strip=True)
