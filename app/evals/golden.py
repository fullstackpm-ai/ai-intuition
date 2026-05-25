from __future__ import annotations

from pathlib import Path

from app.llm.edit import edit_insights
from app.llm.extract import extract_insights
from app.models import NormalizedItem
from app.store.files import read_markdown


def run_prompt_design_golden(path: Path) -> list:
    metadata, text = read_markdown(path)
    item = NormalizedItem(
        id="golden_prompt_design_principles",
        raw_artifact_id="golden_prompt_design_principles",
        source_id=str(metadata.get("source_id", "manual")),
        lane="manual",
        title=str(metadata.get("title", "Prompt Design Principles")),
        url=metadata.get("url"),
        published_at=None,
        normalized_path=str(path),
        text=text,
        word_count=len(text.split()),
    )
    return edit_insights(extract_insights(item))
