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


def test_source_registry_loads_rich_source_metadata(tmp_path: Path) -> None:
    path = tmp_path / "sources.yaml"
    path.write_text(
        """
version: 1
sources:
  - id: openai_news
    name: OpenAI News
    priority: p0
    lane: product_patterns
    type: lab_product_and_research_updates
    source_url: https://openai.com/news/
    rss_url: https://openai.com/news/rss.xml
    adapter: rss_or_html
    extraction_goal: Product launches and system patterns.
    include_topics:
      - Codex
      - evals
tooling:
  - id: usetranscribe
    type: transcription_provider
deferred_sources:
  - id: meta_ai_blog
    reason: Later.
"""
    )
    sources = load_sources(path)
    assert len(sources) == 1
    source = sources[0]
    assert source.id == "openai_news"
    assert source.priority == "p0"
    assert source.adapter == "rss_or_html"
    assert source.include_topics == ["Codex", "evals"]
    assert source.urls == ["https://openai.com/news/rss.xml", "https://openai.com/news/"]
