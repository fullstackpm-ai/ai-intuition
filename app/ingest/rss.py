from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import httpx

from app.ingest.discovery import DateWindow, DiscoveredItem, discover_source
from app.ingest.html import ingest_html_url
from app.ingest.substack import extract_youtube_urls_from_substack_html, ingest_substack_transcript_url
from app.ingest.transcript import UseTranscribeClient, write_transcript_raw_artifact
from app.logging import console
from app.models import RawArtifact, Source
from app.observability.run import RunContext, classify_exception


def ingest_discovered_articles(source: Source, items: list[DiscoveredItem], raw_root: Path) -> list[RawArtifact]:
    artifacts: list[RawArtifact] = []
    for item in items:
        if item.item_type != "article":
            continue
        artifacts.append(
            ingest_html_url(
                source,
                item.url,
                raw_root,
                title=item.title,
                published_at=item.published_at,
                metadata=item.metadata,
            )
        )
    return artifacts


def ingest_discovered_podcast_pages(
    source: Source,
    items: list[DiscoveredItem],
    raw_root: Path,
    transcript_client: UseTranscribeClient | None = None,
    run_context: RunContext | None = None,
) -> list[RawArtifact]:
    artifacts: list[RawArtifact] = []
    client = transcript_client or UseTranscribeClient()
    for item in items:
        if item.item_type != "podcast_episode" or item.metadata.get("platform") != "rss":
            continue
        try:
            artifacts.append(_ingest_podcast_episode_page(source, item, raw_root, client, run_context))
        except ValueError as exc:
            console.print(f"[yellow]Skipped {item.url}: {exc}[/yellow]")
    return artifacts


def _ingest_podcast_episode_page(
    source: Source,
    item: DiscoveredItem,
    raw_root: Path,
    transcript_client: UseTranscribeClient,
    run_context: RunContext | None = None,
) -> RawArtifact:
    response = httpx.get(item.url, follow_redirects=True, timeout=30)
    response.raise_for_status()
    youtube_urls = extract_youtube_urls_from_substack_html(response.text)
    for youtube_url in youtube_urls:
        if run_context:
            run_context.event(
                "ingest",
                "fallback_attempted",
                "Trying embedded YouTube transcript via useTranscribe.",
                source=source,
                url=youtube_url,
                metadata={"episode_url": item.url, "fallback": "youtube_usetranscribe"},
            )
        try:
            result = transcript_client.transcribe_youtube_url(youtube_url)
            result = replace(result, published_at=result.published_at or item.published_at)
            if run_context:
                run_context.event(
                    "ingest",
                    "fallback_succeeded",
                    "Embedded YouTube transcript succeeded.",
                    source=source,
                    url=youtube_url,
                    metadata={"episode_url": item.url, "fallback": "youtube_usetranscribe"},
                )
            return write_transcript_raw_artifact(result, source, raw_root)
        except RuntimeError as exc:
            if run_context:
                outcome, retryability, error = classify_exception(exc)
                run_context.event(
                    "ingest",
                    "fallback_failed",
                    "Embedded YouTube transcript failed.",
                    level="warning",
                    source=source,
                    url=youtube_url,
                    metadata={
                        "episode_url": item.url,
                        "fallback": "youtube_usetranscribe",
                        "outcome": outcome,
                        "retryability": retryability,
                        "error": error.model_dump(mode="json"),
                    },
                )
            console.print(f"[yellow]useTranscribe skipped {youtube_url}: {exc}[/yellow]")
    if run_context:
        run_context.event(
            "ingest",
            "fallback_attempted",
            "Trying Substack transcript fallback.",
            source=source,
            url=item.url,
            metadata={"fallback": "substack_transcript"},
        )
    artifact = ingest_substack_transcript_url(
        source,
        item.url,
        raw_root,
        title=item.title,
        published_at=item.published_at,
    )
    if run_context:
        run_context.event(
            "ingest",
            "fallback_succeeded",
            "Substack transcript fallback succeeded.",
            source=source,
            url=item.url,
            metadata={"fallback": "substack_transcript"},
        )
    return artifact


def ingest_rss_or_html_source(
    source: Source,
    raw_root: Path,
    limit: int = 5,
    window: DateWindow | None = None,
) -> list[RawArtifact]:
    discovered = discover_source(source, window or DateWindow(), limit=limit)
    return ingest_discovered_articles(source, discovered, raw_root)


def ingest_podcast_episode_pages(
    source: Source,
    raw_root: Path,
    limit: int = 5,
    window: DateWindow | None = None,
    run_context: RunContext | None = None,
) -> list[RawArtifact]:
    discovered = discover_source(source, window or DateWindow(), limit=limit)
    return ingest_discovered_podcast_pages(source, discovered, raw_root, run_context=run_context)
