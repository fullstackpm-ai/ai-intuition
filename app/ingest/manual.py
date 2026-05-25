from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path

from app.ids import content_hash, deterministic_id
from app.models import RawArtifact, Source
from app.store.files import read_markdown, write_markdown
from app.time import now_utc


def ingest_manual_file(path: Path, source: Source, raw_root: Path) -> RawArtifact:
    metadata, body = read_markdown(path)
    title = str(metadata.get("title") or path.stem.replace("-", " ").title())
    published_at = metadata.get("published_at")
    if isinstance(published_at, str):
        published_at = datetime.fromisoformat(published_at)
    elif isinstance(published_at, date) and not isinstance(published_at, datetime):
        published_at = datetime.combine(published_at, time.min)
    digest = content_hash(body)
    artifact_id = deterministic_id(str(metadata.get("source_id") or source.id), title, published_at, body)
    destination = raw_root / "manual" / f"{artifact_id}.md"
    write_markdown(
        destination,
        {
            "source_id": metadata.get("source_id") or source.id,
            "title": title,
            "url": metadata.get("url"),
            "published_at": published_at.isoformat() if published_at else None,
        },
        body,
    )
    return RawArtifact(
        id=artifact_id,
        source_id=str(metadata.get("source_id") or source.id),
        source_name=source.name,
        lane=str(metadata.get("lane") or source.lane),
        source_type="manual",
        title=title,
        url=metadata.get("url"),
        author=metadata.get("author"),
        published_at=published_at,
        discovered_at=now_utc(),
        raw_path=str(destination),
        content_hash=digest,
        metadata=dict(metadata),
    )


def ingest_manual_directory(source: Source, root: Path) -> list[RawArtifact]:
    if not source.path:
        return []
    source_path = root / source.path
    if not source_path.exists():
        return []
    artifacts = []
    for path in sorted(source_path.glob("*.md")):
        artifacts.append(ingest_manual_file(path, source, root / "data" / "raw"))
    return artifacts
