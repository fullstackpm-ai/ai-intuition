from __future__ import annotations

from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from app.ingest.substack import extract_substack_transcript_candidates, extract_youtube_urls_from_substack_html
from app.models import NormalizedItem, RawArtifact
from app.store.files import read_markdown, write_markdown


BOILERPLATE_LINES = {
    "Quick links",
    "Paper",
    "Share Copy link ×",
    "Copy link ×",
    "Share",
    "Ready for more?",
}
PAYWALL_MARKERS = (
    "Subscribe to Stratechery Plus for full access",
    "Already subscribed?",
    "$15 / month or $150 / year",
)


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
        raw_metadata, text = read_markdown(raw_path)
        metadata = {**artifact.metadata, **raw_metadata}
        notes = str(metadata.get("extraction_notes") or metadata.get("transcript_provider") or "manual markdown")
    else:
        metadata = dict(artifact.metadata)
        html = raw_path.read_text()
        if artifact.source_id == "lenny_newsletter":
            metadata = {**_lenny_legacy_html_metadata(html), **metadata}
        text = _html_to_text(html)
        notes = "html via BeautifulSoup"
    text, quality_metrics = _clean_and_score_text(artifact, text.strip(), metadata)
    quality = _quality_metadata(artifact, text, metadata, quality_metrics, notes)
    destination = output_root / f"{artifact.id}.md"
    frontmatter = {
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
        **quality,
    }
    write_markdown(destination, frontmatter, text)
    model_quality = {key: value for key, value in quality.items() if key != "extraction_notes"}
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
        **model_quality,
    )


def _clean_and_score_text(artifact: RawArtifact, text: str, metadata: dict[str, Any]) -> tuple[str, dict[str, float]]:
    lines = [line.strip() for line in text.splitlines()]
    nonempty = [line for line in lines if line]
    duplicate_extra = len(nonempty) - len(dict.fromkeys(nonempty))
    duplicate_line_ratio = duplicate_extra / len(nonempty) if nonempty else 0.0

    cleaned_lines: list[str] = []
    seen: set[str] = set()
    boilerplate_count = 0
    stop_at_related = False
    for line in nonempty:
        if artifact.source_id == "google_research_blog" and line in {"Other posts of interest", "Labels:"}:
            stop_at_related = True
        if stop_at_related:
            boilerplate_count += 1
            continue
        if line in BOILERPLATE_LINES:
            boilerplate_count += 1
            continue
        if line in seen:
            duplicate_counted = line in metadata.get("duplicate_exemptions", [])
            if not duplicate_counted:
                continue
        seen.add(line)
        cleaned_lines.append(line)

    if artifact.source_id == "lenny_newsletter" and metadata.get("primary_content_kind") == "show_notes":
        boilerplate_count += sum(1 for line in cleaned_lines if line.startswith(("Listen or watch", "Brought to you by:", "Production and marketing")))

    boilerplate_ratio = boilerplate_count / len(nonempty) if nonempty else 0.0
    return "\n\n".join(cleaned_lines).strip(), {
        "duplicate_line_ratio": round(duplicate_line_ratio, 3),
        "boilerplate_ratio": round(boilerplate_ratio, 3),
    }


def _lenny_legacy_html_metadata(html: str) -> dict[str, Any]:
    candidates = extract_substack_transcript_candidates(html)
    youtube_urls = extract_youtube_urls_from_substack_html(html)
    if not candidates and not youtube_urls:
        return {}
    return {
        "detected_page_type": "hybrid_media_post",
        "primary_content_kind": "show_notes",
        "selected_normalizer": "substack_show_notes_fallback",
        "classification_confidence": 0.7,
        "classification_signals": [
            signal
            for signal in ["substack_media_transcript_metadata" if candidates else "", "embedded_youtube" if youtube_urls else ""]
            if signal
        ],
        "quality_status": "degraded",
        "degraded_reason": "Historical Lenny HTML artifact contains media/transcript signals but was normalized from visible show notes.",
    }


def _quality_metadata(
    artifact: RawArtifact,
    text: str,
    metadata: dict[str, Any],
    metrics: dict[str, float],
    notes: str,
) -> dict[str, Any]:
    detected_page_type = metadata.get("detected_page_type") or _default_page_type(artifact)
    primary_content_kind = metadata.get("primary_content_kind") or _default_content_kind(artifact)
    selected_normalizer = metadata.get("selected_normalizer") or _default_normalizer(artifact)
    signals = list(metadata.get("classification_signals") or [])
    quality_flags = list(metadata.get("quality_flags") or [])
    quality_status = metadata.get("quality_status") or "usable"
    degraded_reason = metadata.get("degraded_reason")
    word_count = len(text.split())

    if metrics["duplicate_line_ratio"] > 0.15:
        quality_flags.append("duplicate_line_ratio_high")
    if metrics["boilerplate_ratio"] > 0.30:
        quality_flags.append("boilerplate_ratio_high")
    if any(marker in text for marker in PAYWALL_MARKERS):
        detected_page_type = "partial_paywalled_page"
        primary_content_kind = "paywall_copy"
        selected_normalizer = "stratechery_paywall_detector"
        quality_status = "rejected"
        degraded_reason = "Accessible page is dominated by Stratechery subscription/paywall copy."
        quality_flags.append("paywall_dominant")
    if artifact.source_id == "lenny_newsletter" and primary_content_kind == "show_notes":
        quality_status = "degraded"
        degraded_reason = degraded_reason or "Podcast/video page only yielded show notes, not a full transcript."
        quality_flags.append("show_notes_without_transcript")
    if word_count < 250:
        quality_flags.append("low_word_count")

    return {
        "detected_page_type": detected_page_type,
        "primary_content_kind": primary_content_kind,
        "selected_normalizer": selected_normalizer,
        "classification_confidence": float(metadata.get("classification_confidence") or 0.5),
        "classification_signals": sorted(set(str(signal) for signal in signals)),
        "quality_status": quality_status,
        "quality_flags": sorted(set(quality_flags)),
        "degraded_reason": degraded_reason,
        "duplicate_line_ratio": metrics["duplicate_line_ratio"],
        "boilerplate_ratio": metrics["boilerplate_ratio"],
        "extraction_notes": notes,
    }


def _default_page_type(artifact: RawArtifact) -> str:
    if artifact.source_type == "podcast_transcript":
        return "podcast_episode_page"
    return "article_page"


def _default_content_kind(artifact: RawArtifact) -> str:
    if artifact.source_type == "podcast_transcript":
        return "full_transcript"
    return "article_body"


def _default_normalizer(artifact: RawArtifact) -> str:
    if artifact.source_type == "podcast_transcript":
        return "markdown_transcript"
    return "generic_html"


def _portable_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)
