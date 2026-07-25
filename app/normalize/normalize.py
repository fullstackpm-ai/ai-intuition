from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from app.models import NormalizedItem, RawArtifact
from app.store.files import read_markdown, write_markdown


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "nav", "footer"]):
        node.decompose()
    title = soup.find("title")
    pieces = []
    if title and title.get_text(strip=True):
        pieces.append(f"# {title.get_text(strip=True)}")
    text = "\n\n".join(
        block.get_text(" ", strip=True)
        for block in soup.find_all(["h1", "h2", "h3", "p", "li"])
        if block.get_text(" ", strip=True)
    )
    pieces.append(text)
    return "\n\n".join(piece for piece in pieces if piece).strip()


def normalize_raw_artifact(artifact: RawArtifact, output_root: Path) -> NormalizedItem:
    raw_path = Path(artifact.raw_path)
    portable_raw_path = _portable_path(raw_path)
    if raw_path.suffix.lower() in {".md", ".markdown"}:
        _, text = read_markdown(raw_path)
        notes = "manual markdown"
    else:
        text = _html_to_text(raw_path.read_text())
        notes = "html via BeautifulSoup"
    text = text.strip()
    destination = output_root / f"{artifact.id}.md"
    write_markdown(
        destination,
        {
            "id": artifact.id,
            "raw_artifact_id": artifact.id,
            "source_id": artifact.source_id,
            "source_name": artifact.source_name,
            "source_type": artifact.source_type,
            "lane": artifact.lane,
            "title": artifact.title,
            "url": artifact.url,
            "published_at": artifact.published_at.isoformat() if artifact.published_at else None,
            "raw_path": portable_raw_path,
        },
        text,
    )
    return NormalizedItem(
        id=artifact.id,
        raw_artifact_id=artifact.id,
        source_id=artifact.source_id,
        source_name=artifact.source_name,
        source_type=artifact.source_type,
        lane=artifact.lane,
        title=artifact.title,
        url=artifact.url,
        published_at=artifact.published_at,
        raw_path=portable_raw_path,
        normalized_path=str(destination),
        text=text,
        word_count=len(text.split()),
        extraction_notes=notes,
    )


def _portable_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)
