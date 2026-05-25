from __future__ import annotations

from pathlib import Path

import yaml

from app.models import Source, SourceRegistry


ROOT = Path.cwd()
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "state.sqlite3"


def load_sources(path: Path | None = None) -> list[Source]:
    source_path = path or ROOT / "sources.yaml"
    payload = yaml.safe_load(source_path.read_text()) or {"sources": []}
    return SourceRegistry.model_validate(payload).sources


def enabled_sources(source_id: str | None = None) -> list[Source]:
    sources = [source for source in load_sources() if source.enabled]
    if source_id:
        sources = [source for source in sources if source.id == source_id]
    return sources
