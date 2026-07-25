from __future__ import annotations

from datetime import datetime
from pathlib import Path

import httpx

from app.ids import content_hash, deterministic_id
from app.models import RawArtifact, Source
from app.time import now_utc


def fetch_html(url: str) -> str:
    response = httpx.get(url, follow_redirects=True, timeout=20)
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
