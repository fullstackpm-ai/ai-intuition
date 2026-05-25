from pathlib import Path

from app.config import load_sources


def test_source_registry_loads_yaml(tmp_path: Path) -> None:
    path = tmp_path / "sources.yaml"
    path.write_text(
        """
sources:
  - id: manual
    name: Manual Inputs
    lane: manual
    type: manual
    path: data/raw/manual
    enabled: true
"""
    )
    sources = load_sources(path)
    assert len(sources) == 1
    assert sources[0].id == "manual"
