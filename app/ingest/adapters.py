from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ingest.discovery import DiscoveredItem
from app.models import Source


ANTHROPIC_ARTICLE_SOURCES = {
    "anthropic_research",
    "anthropic_engineering",
    "anthropic_alignment_science",
    "anthropic_frontier_red_team",
}


@dataclass(frozen=True)
class HtmlAdapterDecision:
    """Deterministic pre-normalization routing metadata for an HTML/feed item."""

    name: str
    metadata: dict[str, Any]
    use_feed_content: bool = False


def select_html_adapter(source: Source, item: DiscoveredItem) -> HtmlAdapterDecision:
    """Select the narrow source adapter before the raw artifact is written."""
    if source.id == "google_research_blog":
        return HtmlAdapterDecision(
            "google_research_article",
            {
                "detected_page_type": "article_page",
                "primary_content_kind": "article_body",
                "selected_normalizer": "google_research_article",
                "classification_confidence": 0.95,
                "classification_signals": ["source_adapter:google_research", "article_candidate"],
                "quality_status": "usable",
                "fallback_attempts": [],
                "selected_fallback": None,
            },
        )
    if source.id in ANTHROPIC_ARTICLE_SOURCES:
        return HtmlAdapterDecision(
            "anthropic_article",
            {
                "detected_page_type": "article_page",
                "primary_content_kind": "article_body",
                "selected_normalizer": "anthropic_article",
                "classification_confidence": 0.95,
                "classification_signals": ["source_adapter:anthropic", "article_candidate"],
                "quality_status": "usable",
                "fallback_attempts": [],
                "selected_fallback": None,
            },
        )
    if source.id == "stratechery":
        authorized = bool(item.metadata.get("authorized_full_feed"))
        has_feed_content = bool(item.metadata.get("full_feed_content"))
        if authorized and has_feed_content:
            return HtmlAdapterDecision(
                "stratechery_authorized_feed",
                {
                    "detected_page_type": "article_page",
                    "primary_content_kind": "full_feed_content",
                    "selected_normalizer": "stratechery_authorized_feed",
                    "classification_confidence": 0.98,
                    "classification_signals": ["source_adapter:stratechery", "authorized_full_feed_content"],
                    "quality_status": "usable",
                    "fallback_attempts": [],
                    "selected_fallback": "authorized_full_feed_content",
                },
                use_feed_content=True,
            )
        return HtmlAdapterDecision(
            "stratechery_public_page",
            {
                "detected_page_type": "article_page",
                "primary_content_kind": "article_body",
                "selected_normalizer": "stratechery_public_page",
                "classification_confidence": 0.85,
                "classification_signals": ["source_adapter:stratechery", "public_page"],
                "quality_status": "usable",
                "quality_flags": ["authorized_full_feed_not_used"] if authorized else [],
                "fallback_attempts": [],
                "selected_fallback": None,
            },
        )
    return HtmlAdapterDecision(
        "generic_html_fallback",
        {
            "detected_page_type": "article_page",
            "primary_content_kind": "article_body",
            "selected_normalizer": "generic_html_fallback",
            "classification_confidence": 0.4,
            "classification_signals": ["generic_html_fallback"],
            "quality_status": "usable",
            "quality_flags": ["generic_fallback_used"],
            "fallback_attempts": [],
            "selected_fallback": "generic_html_fallback",
        },
    )
