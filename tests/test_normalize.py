from __future__ import annotations

from datetime import UTC, datetime

from app.models import RawArtifact
from app.normalize.normalize import normalize_raw_artifact
from app.store.files import read_markdown


def test_normalized_item_uses_repo_relative_raw_path(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    raw_path = tmp_path / "data/raw/lab-posts/example.html"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("<html><title>Example</title><p>Agents need harnesses.</p></html>")
    artifact = RawArtifact(
        id="example",
        source_id="anthropic_research",
        source_name="Anthropic Research",
        lane="reliability_failures",
        source_type="html",
        title="Example",
        url="https://example.com/article",
        published_at=datetime(2026, 7, 24, tzinfo=UTC),
        discovered_at=datetime(2026, 7, 25, tzinfo=UTC),
        raw_path=str(raw_path),
        content_hash="hash",
    )

    normalized = normalize_raw_artifact(artifact, tmp_path / "data/normalized")
    metadata, _ = read_markdown(tmp_path / normalized.normalized_path)

    assert normalized.raw_path == "data/raw/lab-posts/example.html"
    assert metadata["raw_path"] == "data/raw/lab-posts/example.html"
