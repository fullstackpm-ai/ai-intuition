from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
import json
import re
from typing import Literal
from urllib.parse import parse_qs, urljoin, urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup

from app.models import Source


ItemType = Literal["article", "podcast_episode", "video"]
HTTP_HEADERS = {"User-Agent": "ai-intuition-compiler/0.1 (+source discovery)"}
MONTH_DATE_PATTERN = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|"
    r"January|February|March|April|June|July|August|September|October|November|December)"
    r"\.?\s+\d{1,2},\s+\d{4}\b"
)
YEAR_ONLY_PATTERN = re.compile(r"^\d{4}$")
ANTHROPIC_CATEGORIES = (
    "Frontier Red Team",
    "Economic Research",
    "Societal Impacts",
    "Interpretability",
    "Alignment",
    "Research",
    "Policy",
)
OPENAI_RESEARCH_CATEGORIES = ("Research", "Publication", "Milestone", "Conclusion")
DATE_ENRICHMENT_SOURCE_IDS = {
    "google_deepmind_blog",
    "anthropic_alignment_science",
    "anthropic_engineering",
}
SOURCE_HEALTH_REVIEW_IDS = {"anthropic_frontier_red_team"}
ARTICLE_DATE_META_KEYS = {
    "article:published_time",
    "date",
    "datepublished",
    "dc.date",
    "dc.date.issued",
    "publishdate",
    "pubdate",
    "published",
    "published_time",
}


@dataclass(frozen=True)
class DateWindow:
    start: datetime | None = None
    end: datetime | None = None

    def contains(self, value: datetime | None) -> bool:
        if value is None:
            return True
        if self.start and value < self.start:
            return False
        if self.end and value > self.end:
            return False
        return True


@dataclass(frozen=True)
class DiscoveredItem:
    source_id: str
    title: str
    url: str
    item_type: ItemType
    published_at: datetime | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class DiscoveryError(RuntimeError):
    pass


def discover_source(source: Source, window: DateWindow, limit: int = 10) -> list[DiscoveredItem]:
    adapter = source.adapter or source.type
    if adapter == "openai_research_rss":
        return discover_openai_research_rss(source, window, limit)
    if adapter == "rss_or_html":
        return discover_rss_or_html(source, window, limit)
    if adapter == "html_index":
        return discover_html_index(source, window, limit, item_type="article")
    if adapter == "podcast_episode_page_or_youtube":
        return discover_podcast_page_or_youtube(source, window, limit)
    raise DiscoveryError(f"Unsupported discovery adapter: {adapter}")


def discover_openai_research_rss(source: Source, window: DateWindow, limit: int = 10) -> list[DiscoveredItem]:
    """Discover only first-party Research-tagged entries from OpenAI's public RSS feed."""
    if not source.rss_url:
        raise DiscoveryError("openai_research_rss requires source.rss_url")

    response = httpx.get(source.rss_url, follow_redirects=True, timeout=20, headers=HTTP_HEADERS)
    response.raise_for_status()
    parsed = feedparser.parse(response.text)
    entries = getattr(parsed, "entries", [])
    if getattr(parsed, "bozo", False):
        raise DiscoveryError("OpenAI Research RSS payload is malformed")

    discovered: list[DiscoveredItem] = []
    research_tagged_entries = 0
    for entry in entries:
        categories = _entry_categories(entry)
        if "research" not in {category.lower() for category in categories}:
            continue
        research_tagged_entries += 1
        link = getattr(entry, "link", None)
        if not link or not _looks_like_candidate(source, str(link), "openai.com", "article"):
            continue
        published_at = _entry_date(entry)
        if published_at is None or not window.contains(published_at):
            continue
        title = _clean_candidate_title(source, str(getattr(entry, "title", None) or _title_from_url(str(link))))
        discovered.append(
            DiscoveredItem(
                source_id=source.id,
                title=title,
                url=str(link),
                item_type="article",
                published_at=published_at,
                metadata={
                    "discovered_via": source.rss_url,
                    "adapter": "openai_research_rss",
                    "entry_categories": categories,
                    "category_filter": "Research",
                    "research_tagged_entries": research_tagged_entries,
                },
            )
        )
        if len(discovered) >= limit:
            break
    return _dedupe(discovered)


def discover_rss_or_html(source: Source, window: DateWindow, limit: int = 10) -> list[DiscoveredItem]:
    discovered: list[DiscoveredItem] = []
    for url in source.urls:
        response = httpx.get(url, follow_redirects=True, timeout=20, headers=HTTP_HEADERS)
        response.raise_for_status()
        parsed = feedparser.parse(response.text)
        entries = getattr(parsed, "entries", [])
        if entries:
            for entry in entries:
                link = getattr(entry, "link", None)
                if not link:
                    continue
                published_at = _entry_date(entry)
                if not window.contains(published_at):
                    continue
                discovered.append(
                    DiscoveredItem(
                        source_id=source.id,
                        title=str(getattr(entry, "title", None) or _title_from_url(link)),
                        url=str(link),
                        item_type="article",
                        published_at=published_at,
                        metadata={
                            "discovered_via": url,
                            "adapter": "rss_or_html",
                            "authorized_full_feed": bool(source.rss_url_env and url != source.rss_url),
                            "full_feed_content": _entry_full_content(entry),
                        },
                    )
                )
                if len(discovered) >= limit:
                    return _dedupe(discovered)
        else:
            discovered.extend(discover_html_index(source, window, limit - len(discovered), item_type="article", urls=[url]))
        if len(discovered) >= limit:
            return _dedupe(discovered[:limit])
    return _dedupe(discovered[:limit])


def discover_html_index(
    source: Source,
    window: DateWindow,
    limit: int = 10,
    item_type: ItemType = "article",
    urls: list[str] | None = None,
) -> list[DiscoveredItem]:
    discovered: list[DiscoveredItem] = []
    candidate_limit = max(limit, min(limit * 5, 25))
    for index_url in urls or source.urls:
        response = httpx.get(index_url, follow_redirects=True, timeout=20, headers=HTTP_HEADERS)
        response.raise_for_status()
        discovered.extend(_discover_links_from_html(source, str(response.url), response.text, item_type))
        if len(discovered) >= candidate_limit:
            break
    enriched = _enrich_missing_dates(source, _dedupe(discovered[:candidate_limit]))
    return [item for item in enriched if window.contains(item.published_at)][:limit]


def classify_source_health(source: Source, items: list[DiscoveredItem]) -> str:
    if items:
        return "healthy"
    if source.id in SOURCE_HEALTH_REVIEW_IDS:
        return "needs_source_path_review"
    return "healthy_empty"


def discover_podcast_page_or_youtube(source: Source, window: DateWindow, limit: int = 10) -> list[DiscoveredItem]:
    discovered: list[DiscoveredItem] = []
    for url in source.urls:
        if _youtube_video_id(url):
            discovered.append(
                DiscoveredItem(
                    source_id=source.id,
                    title=_title_from_url(url),
                    url=url,
                    item_type="video",
                    metadata={"adapter": "podcast_episode_page_or_youtube"},
                )
            )
            continue
        if _spotify_episode_id(url):
            discovered.append(
                DiscoveredItem(
                    source_id=source.id,
                    title=_title_from_url(url),
                    url=url,
                    item_type="podcast_episode",
                    metadata={"adapter": "podcast_episode_page_or_youtube", "platform": "spotify"},
                )
            )
            continue
        response = httpx.get(url, follow_redirects=True, timeout=20, headers=HTTP_HEADERS)
        response.raise_for_status()
        parsed = feedparser.parse(response.text)
        entries = getattr(parsed, "entries", [])
        if entries:
            for entry in entries:
                link = getattr(entry, "link", None)
                if not link:
                    continue
                published_at = _entry_date(entry)
                if not window.contains(published_at):
                    continue
                metadata: dict[str, object] = {
                    "discovered_via": url,
                    "adapter": "podcast_episode_page_or_youtube",
                    "platform": "rss",
                }
                audio_url = _entry_audio_url(entry)
                if audio_url:
                    metadata["audio_url"] = audio_url
                discovered.append(
                    DiscoveredItem(
                        source_id=source.id,
                        title=str(getattr(entry, "title", None) or _title_from_url(link)),
                        url=str(link),
                        item_type="podcast_episode",
                        published_at=published_at,
                        metadata=metadata,
                    )
                )
                if len(discovered) >= limit:
                    return _dedupe(discovered)
            continue
        discovered.extend(_discover_links_from_html(source, url, response.text, item_type="video"))
        discovered.extend(_discover_links_from_html(source, url, response.text, item_type="podcast_episode"))
        if len(discovered) >= limit:
            break
    return _dedupe([item for item in discovered if window.contains(item.published_at)][:limit])


def _discover_links_from_html(source: Source, base_url: str, html: str, item_type: ItemType) -> list[DiscoveredItem]:
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(base_url).netloc.removeprefix("www.")
    items: list[DiscoveredItem] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        url = urljoin(base_url, href)
        if not _looks_like_candidate(source, url, base_domain, item_type):
            continue
        raw_title = " ".join(anchor.get_text(" ", strip=True).split()) or _title_from_url(url)
        if not _source_allows_candidate_text(source, raw_title):
            continue
        title = _clean_candidate_title(source, raw_title)
        published_at = _published_at_near_anchor(anchor)
        items.append(
            DiscoveredItem(
                source_id=source.id,
                title=title,
                url=url,
                item_type=item_type,
                published_at=published_at,
                metadata={"discovered_via": base_url, "adapter": source.adapter or source.type},
            )
        )
    return items


def _enrich_missing_dates(source: Source, items: list[DiscoveredItem]) -> list[DiscoveredItem]:
    if source.id not in DATE_ENRICHMENT_SOURCE_IDS:
        return items

    enriched: list[DiscoveredItem] = []
    for item in items:
        if item.published_at is not None or item.item_type != "article":
            enriched.append(item)
            continue
        metadata = dict(item.metadata)
        metadata["date_enrichment_checked_url"] = item.url
        try:
            response = httpx.get(item.url, follow_redirects=True, timeout=20, headers=HTTP_HEADERS)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            metadata["date_enrichment_status"] = "fetch_failed"
            metadata["date_enrichment_error"] = exc.__class__.__name__
            enriched.append(replace(item, metadata=metadata))
            continue

        published_at, via = _published_at_from_article_html(response.text)
        if published_at:
            metadata["date_enrichment_status"] = "success"
            metadata["date_enriched_via"] = via
            enriched.append(replace(item, published_at=published_at, metadata=metadata))
            continue

        metadata["date_enrichment_status"] = "no_date_found"
        enriched.append(replace(item, metadata=metadata))
    return enriched


def _published_at_from_article_html(html: str) -> tuple[datetime | None, str | None]:
    soup = BeautifulSoup(html, "html.parser")

    jsonld_date = _published_at_from_jsonld(soup)
    if jsonld_date:
        return jsonld_date, "json_ld"

    for meta in soup.find_all("meta"):
        key = str(meta.get("property") or meta.get("name") or meta.get("itemprop") or "").strip().lower()
        if key not in ARTICLE_DATE_META_KEYS:
            continue
        parsed = _date_from_raw_value(meta.get("content"))
        if parsed:
            return parsed, f"meta:{key}"

    for time_tag in soup.find_all("time"):
        parsed = _date_from_raw_value(time_tag.get("datetime") or time_tag.get_text(" ", strip=True))
        if parsed:
            return parsed, "time"

    for text in soup.stripped_strings:
        parsed = _date_from_visible_metadata_text(text)
        if parsed:
            return parsed, "visible_text"

    return None, None


def _published_at_from_jsonld(soup: BeautifulSoup) -> datetime | None:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        parsed = _published_at_from_jsonld_payload(payload)
        if parsed:
            return parsed
    return None


def _published_at_from_jsonld_payload(payload: object) -> datetime | None:
    if isinstance(payload, list):
        for item in payload:
            parsed = _published_at_from_jsonld_payload(item)
            if parsed:
                return parsed
        return None
    if not isinstance(payload, dict):
        return None

    for key in ("datePublished", "dateCreated", "uploadDate", "dateModified"):
        parsed = _date_from_raw_value(payload.get(key))
        if parsed:
            return parsed

    for nested_key in ("@graph", "mainEntity", "mainEntityOfPage"):
        parsed = _published_at_from_jsonld_payload(payload.get(nested_key))
        if parsed:
            return parsed
    return None


def _looks_like_candidate(source: Source, url: str, base_domain: str, item_type: ItemType) -> bool:
    parsed = urlparse(url)
    domain = parsed.netloc.removeprefix("www.")
    if item_type == "video":
        return bool(_youtube_video_id(url))
    if item_type == "podcast_episode":
        return bool(_spotify_episode_id(url))
    if domain != base_domain:
        return False
    path = parsed.path.strip("/")
    if not path:
        return False
    if ":" in path or path.lower().startswith("javascript"):
        return False
    path_parts = [part for part in path.split("/") if part]
    blocked_exact = {"research", "news", "engineering", "blog", "podcast", "feed", "rss.xml"}
    blocked_parts = {"team", "rss", "feed", "archive", "tags", "tag", "category", "label"}
    if path in blocked_exact or any(part in blocked_parts for part in path_parts):
        return False

    if source.id == "openai_research":
        return domain == "openai.com" and path.startswith("index/")
    if source.id == "google_deepmind_blog":
        return domain == "deepmind.google" and path.startswith("blog/") and len(path_parts) > 1
    if source.id == "google_research_blog":
        return (
            domain == "research.google"
            and path.startswith("blog/")
            and len(path_parts) > 1
            and not any(YEAR_ONLY_PATTERN.fullmatch(part) for part in path_parts)
        )
    if source.id == "anthropic_alignment_science":
        return domain == "alignment.anthropic.com" and len(path_parts) >= 2 and YEAR_ONLY_PATTERN.fullmatch(path_parts[0]) is not None
    if source.id == "anthropic_engineering":
        return domain == "anthropic.com" and path.startswith("engineering/") and len(path_parts) > 1
    if source.id in {"anthropic_research", "anthropic_frontier_red_team"}:
        return domain == "anthropic.com" and path.startswith("research/") and len(path_parts) > 1

    if any(YEAR_ONLY_PATTERN.fullmatch(part) for part in path_parts):
        return False

    return any(part in parsed.path for part in ["/research/", "/news/", "/engineering/", "/blog/", "/index/"])


def _source_allows_candidate_text(source: Source, title: str) -> bool:
    if source.id == "openai_research":
        return any(re.search(rf"\b{re.escape(category)}\b\s+{MONTH_DATE_PATTERN.pattern}", title) for category in OPENAI_RESEARCH_CATEGORIES)
    return True


def _clean_candidate_title(source: Source, title: str) -> str:
    cleaned = " ".join(title.split())
    if source.id == "openai_research":
        cleaned = re.sub(
            rf"\s+(?:{'|'.join(re.escape(category) for category in OPENAI_RESEARCH_CATEGORIES)})\s+{MONTH_DATE_PATTERN.pattern}\s*$",
            "",
            cleaned,
        )
    elif source.id.startswith("anthropic"):
        cleaned = MONTH_DATE_PATTERN.sub("", cleaned, count=1).strip()
        for category in ANTHROPIC_CATEGORIES:
            if cleaned.startswith(f"{category} "):
                cleaned = cleaned[len(category) + 1 :]
                break
        cleaned = MONTH_DATE_PATTERN.sub("", cleaned).strip()
    elif source.id == "google_research_blog":
        cleaned = MONTH_DATE_PATTERN.sub("", cleaned, count=1).strip()
    return cleaned or title


def _youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc.endswith("youtu.be"):
        candidate = parsed.path.strip("/").split("/")[0]
        return candidate if len(candidate) == 11 else None
    if "youtube.com" in parsed.netloc:
        query_id = parse_qs(parsed.query).get("v", [None])[0]
        if query_id and len(query_id) == 11:
            return query_id
        parts = [part for part in parsed.path.split("/") if part]
        for marker in ["embed", "shorts", "live"]:
            if marker in parts:
                index = parts.index(marker)
                if index + 1 < len(parts) and len(parts[index + 1]) == 11:
                    return parts[index + 1]
    return None


def _spotify_episode_id(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc == "open.spotify.com" and parsed.path.startswith("/episode/"):
        candidate = parsed.path.split("/")[2]
        return candidate if len(candidate) == 22 else None
    return None


def _entry_date(entry: object) -> datetime | None:
    raw = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if not raw:
        return None
    try:
        return _ensure_timezone(parsedate_to_datetime(raw))
    except (TypeError, ValueError):
        return None


def _entry_audio_url(entry: object) -> str | None:
    for enclosure in getattr(entry, "enclosures", []):
        href = enclosure.get("href") if hasattr(enclosure, "get") else None
        enclosure_type = enclosure.get("type") if hasattr(enclosure, "get") else None
        if href and (not enclosure_type or str(enclosure_type).startswith("audio/")):
            return str(href)
    return None


def _entry_categories(entry: object) -> list[str]:
    return [
        str(tag.get("term"))
        for tag in getattr(entry, "tags", [])
        if hasattr(tag, "get") and tag.get("term")
    ]


def _entry_full_content(entry: object) -> str | None:
    content = getattr(entry, "content", None)
    if content:
        for candidate in content:
            value = candidate.get("value") if hasattr(candidate, "get") else None
            if value and str(value).strip():
                return str(value)
    return None


def _published_at_near_anchor(anchor: object) -> datetime | None:
    parent = getattr(anchor, "parent", None)
    for node in [anchor, parent, getattr(parent, "parent", None)]:
        if not node:
            continue
        time_tag = node.find("time") if hasattr(node, "find") else None
        raw = None
        if time_tag:
            raw = time_tag.get("datetime") or time_tag.get_text(" ", strip=True)
        if raw:
            try:
                return _ensure_timezone(datetime.fromisoformat(str(raw).replace("Z", "+00:00")))
            except ValueError:
                try:
                    return _ensure_timezone(parsedate_to_datetime(str(raw)))
                except (TypeError, ValueError):
                    pass
    for node in [anchor, parent]:
        if not node:
            continue
        parsed = _date_from_text(node.get_text(" ", strip=True) if hasattr(node, "get_text") else "")
        if parsed:
            return parsed
    return None


def _date_from_text(text: str) -> datetime | None:
    match = MONTH_DATE_PATTERN.search(text)
    if not match:
        return None
    raw = match.group(0).replace(".", "").replace("Sept ", "Sep ")
    try:
        return _ensure_timezone(parsedate_to_datetime(raw))
    except (TypeError, ValueError):
        pass
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=UTC)
        except ValueError:
            pass
    return None


def _date_from_visible_metadata_text(text: str) -> datetime | None:
    normalized = " ".join(text.split())
    if len(normalized) > 96:
        return None
    if MONTH_DATE_PATTERN.match(normalized) or normalized.lower().startswith(("published ", "date ")):
        return _date_from_text(normalized)
    return None


def _date_from_raw_value(raw: object) -> datetime | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    try:
        return _ensure_timezone(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        pass
    try:
        return _ensure_timezone(parsedate_to_datetime(value))
    except (TypeError, ValueError):
        pass
    return _date_from_text(value)


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _title_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/").split("/")[-1]
    return path.replace("-", " ").replace("_", " ").title() or url


def _dedupe(items: list[DiscoveredItem]) -> list[DiscoveredItem]:
    by_url: dict[str, DiscoveredItem] = {}
    for item in items:
        by_url.setdefault(item.url, item)
    return list(by_url.values())
