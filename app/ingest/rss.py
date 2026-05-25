from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
import httpx

from app.ingest.html import ingest_html_url
from app.models import RawArtifact, Source


def _entry_date(entry: object) -> datetime | None:
    raw = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None


def ingest_rss_or_html_source(source: Source, raw_root: Path, limit: int = 5) -> list[RawArtifact]:
    artifacts: list[RawArtifact] = []
    for url in source.urls:
        response = httpx.get(url, follow_redirects=True, timeout=20)
        response.raise_for_status()
        parsed = feedparser.parse(response.text)
        entries = getattr(parsed, "entries", [])
        if entries:
            for entry in entries[:limit]:
                link = getattr(entry, "link", None)
                if not link:
                    continue
                artifacts.append(
                    ingest_html_url(
                        source,
                        link,
                        raw_root,
                        title=getattr(entry, "title", None),
                        published_at=_entry_date(entry),
                    )
                )
        else:
            artifacts.append(ingest_html_url(source, url, raw_root, title=source.name))
    return artifacts
