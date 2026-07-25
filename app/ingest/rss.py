from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.ingest.discovery import DateWindow, DiscoveredItem, discover_source
from app.ingest.adapters import select_html_adapter
from app.ingest.html import ingest_html_url, write_html_raw_artifact, write_markdown_raw_artifact
from app.ingest.substack import (
    extract_substack_transcript_candidates,
    extract_youtube_urls_from_substack_html,
    ingest_substack_media_transcript_url,
    ingest_substack_transcript_url,
)
from app.ingest.transcript import UseTranscribeClient, write_transcript_raw_artifact
from app.logging import console
from app.models import RawArtifact, Source
from app.observability.run import RunContext, classify_exception


def ingest_discovered_articles(
    source: Source,
    items: list[DiscoveredItem],
    raw_root: Path,
    run_context: RunContext | None = None,
) -> list[RawArtifact]:
    artifacts: list[RawArtifact] = []
    for item in items:
        if item.item_type != "article":
            continue
        try:
            if _should_try_substack_media_pipeline(source, item):
                artifacts.append(_ingest_substack_article_or_media(source, item, raw_root, run_context))
                continue
            decision = select_html_adapter(source, item)
            metadata = {key: value for key, value in item.metadata.items() if key != "full_feed_content"}
            metadata.update(decision.metadata)
            if decision.use_feed_content:
                artifacts.append(
                    write_markdown_raw_artifact(
                        source,
                        item.url,
                        str(item.metadata["full_feed_content"]),
                        raw_root,
                        title=item.title,
                        published_at=item.published_at,
                        metadata=metadata,
                    )
                )
                continue
            artifacts.append(
                ingest_html_url(
                    source,
                    item.url,
                    raw_root,
                    title=item.title,
                    published_at=item.published_at,
                    metadata=metadata,
                )
            )
        except httpx.HTTPStatusError as exc:
            if not _should_skip_blocked_article(source, item, exc):
                raise
            outcome, retryability, error = classify_exception(exc)
            error.context = {
                "source_id": source.id,
                "article_url": item.url,
                "discovered_via": item.metadata.get("discovered_via"),
                "policy": "openai_news_blocked_article_item_skip",
            }
            if run_context:
                run_context.event(
                    "ingest",
                    "item_skipped",
                    "Skipped blocked OpenAI News article while continuing source ingest.",
                    level="warning",
                    source=source,
                    url=item.url,
                    metadata={
                        "outcome": outcome,
                        "retryability": retryability,
                        "error": error.model_dump(mode="json"),
                        "item": {
                            "title": item.title,
                            "url": item.url,
                            "published_at": item.published_at.isoformat() if item.published_at else None,
                        },
                    },
                )
            console.print(f"[yellow]Skipped blocked OpenAI News article: {item.url}[/yellow]")
    return artifacts


def _should_try_substack_media_pipeline(source: Source, item: DiscoveredItem) -> bool:
    if source.id not in {"lenny_newsletter", "lenny_podcast", "dwarkesh_podcast"}:
        return False
    return "substack.com" in urlparse(item.url).netloc or "lennysnewsletter.com" in urlparse(item.url).netloc or "dwarkesh.com" in urlparse(item.url).netloc


def _ingest_substack_article_or_media(
    source: Source,
    item: DiscoveredItem,
    raw_root: Path,
    run_context: RunContext | None = None,
) -> RawArtifact:
    response = httpx.get(item.url, follow_redirects=True, timeout=30)
    response.raise_for_status()
    candidates = extract_substack_transcript_candidates(response.text)
    if candidates:
        if run_context:
            run_context.event(
                "ingest",
                "fallback_attempted",
                "Trying first-party Substack transcript/captions.",
                source=source,
                url=item.url,
                metadata={"fallback": "substack_media_transcript", "candidate_count": len(candidates)},
            )
        try:
            artifact = ingest_substack_media_transcript_url(
                source,
                item.url,
                raw_root,
                response.text,
                title=item.title,
                published_at=item.published_at,
            )
            if run_context:
                run_context.event(
                    "ingest",
                    "fallback_succeeded",
                    "First-party Substack transcript/captions succeeded.",
                    source=source,
                    url=item.url,
                    metadata={"fallback": "substack_media_transcript"},
                )
            return artifact
        except ValueError as exc:
            if run_context:
                run_context.event(
                    "ingest",
                    "fallback_failed",
                    "First-party Substack transcript/captions failed.",
                    level="warning",
                    source=source,
                    url=item.url,
                    metadata={"fallback": "substack_media_transcript", "error": str(exc)},
                )
            console.print(f"[yellow]Substack media transcript skipped {item.url}: {exc}[/yellow]")

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
            result = UseTranscribeClient().transcribe_youtube_url(youtube_url)
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

    try:
        if run_context:
            run_context.event(
                "ingest",
                "fallback_attempted",
                "Trying visible Substack transcript section.",
                source=source,
                url=item.url,
                metadata={"fallback": "substack_visible_transcript"},
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
                "Visible Substack transcript section succeeded.",
                source=source,
                url=item.url,
                metadata={"fallback": "substack_visible_transcript"},
            )
        return artifact
    except ValueError:
        pass

    metadata = {
        **item.metadata,
        "detected_page_type": "hybrid_media_post" if candidates or youtube_urls else "article_page",
        "primary_content_kind": "show_notes" if candidates or youtube_urls else "article_body",
        "selected_normalizer": "substack_show_notes_fallback" if candidates or youtube_urls else "generic_html",
        "classification_confidence": 0.7 if candidates or youtube_urls else 0.5,
        "classification_signals": [
            signal
            for signal in ["substack_media_transcript_metadata" if candidates else "", "embedded_youtube" if youtube_urls else ""]
            if signal
        ],
        "quality_status": "degraded" if candidates or youtube_urls else "usable",
        "degraded_reason": "Transcript-capable Substack media was detected but transcript fallbacks failed; only show notes were stored."
        if candidates or youtube_urls
        else None,
    }
    return write_html_raw_artifact(
        source,
        item.url,
        response.text,
        raw_root,
        title=item.title,
        published_at=item.published_at,
        metadata=metadata,
    )


def _should_skip_blocked_article(source: Source, item: DiscoveredItem, exc: httpx.HTTPStatusError) -> bool:
    if source.id != "openai_news":
        return False
    if exc.response.status_code not in {401, 403}:
        return False
    return urlparse(item.url).netloc.removeprefix("www.") == "openai.com"


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
    candidates = extract_substack_transcript_candidates(response.text)
    if candidates:
        if run_context:
            run_context.event(
                "ingest",
                "fallback_attempted",
                "Trying first-party Substack transcript/captions.",
                source=source,
                url=item.url,
                metadata={"fallback": "substack_media_transcript", "candidate_count": len(candidates)},
            )
        try:
            artifact = ingest_substack_media_transcript_url(
                source,
                item.url,
                raw_root,
                response.text,
                title=item.title,
                published_at=item.published_at,
            )
            if run_context:
                run_context.event(
                    "ingest",
                    "fallback_succeeded",
                    "First-party Substack transcript/captions succeeded.",
                    source=source,
                    url=item.url,
                    metadata={"fallback": "substack_media_transcript"},
                )
            return artifact
        except ValueError as exc:
            if run_context:
                run_context.event(
                    "ingest",
                    "fallback_failed",
                    "First-party Substack transcript/captions failed.",
                    level="warning",
                    source=source,
                    url=item.url,
                    metadata={"fallback": "substack_media_transcript", "error": str(exc)},
                )
            console.print(f"[yellow]Substack media transcript skipped {item.url}: {exc}[/yellow]")
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
