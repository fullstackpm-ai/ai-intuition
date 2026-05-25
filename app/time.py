from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("America/Los_Angeles")

def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def now_utc() -> datetime:
    return now_local()


def current_week(dt: datetime | None = None) -> str:
    value = dt or now_local()
    year, week, _ = value.isocalendar()
    return f"{year}-W{week:02d}"


def parse_since(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip().lower()
    if value.endswith("d") and value[:-1].isdigit():
        return now_local() - timedelta(days=int(value[:-1]))
    if value.endswith("h") and value[:-1].isdigit():
        return now_local() - timedelta(hours=int(value[:-1]))
    return datetime.fromisoformat(value.replace("z", "+00:00"))


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None
