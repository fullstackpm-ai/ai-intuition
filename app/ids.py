from __future__ import annotations

import hashlib
import re
from datetime import datetime


def content_hash(text: str | bytes) -> str:
    data = text if isinstance(text, bytes) else text.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:72] or "untitled"


def deterministic_id(source_id: str, title: str, published_at: datetime | None, content: str | bytes) -> str:
    date = published_at.date().isoformat() if published_at else "undated"
    return f"{source_id}_{date}_{slugify(title)}_{content_hash(content)[:8]}"
