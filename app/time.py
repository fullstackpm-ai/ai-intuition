from __future__ import annotations

from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("America/Los_Angeles")

def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def now_utc() -> datetime:
    return now_local()


def current_week(dt: datetime | None = None) -> str:
    value = dt or now_local()
    if value.tzinfo is not None:
        value = value.astimezone(LOCAL_TZ)
    year, week, _ = value.isocalendar()
    return f"{year}-W{week:02d}"


def current_week_start(dt: datetime | None = None) -> datetime:
    value = dt or now_local()
    if value.tzinfo is not None:
        value = value.astimezone(LOCAL_TZ)
    return value.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=value.weekday())


def week_bounds(week: str) -> tuple[datetime, datetime]:
    """Return the local Monday start and exclusive next-Monday boundary for an ISO week."""
    match = re.fullmatch(r"(\d{4})-W(\d{2})", week)
    if not match:
        raise ValueError("Week must use ISO format YYYY-Www, for example 2026-W29.")
    year, week_number = (int(value) for value in match.groups())
    try:
        start = datetime.fromisocalendar(year, week_number, 1).replace(tzinfo=LOCAL_TZ)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO week: {week}.") from exc
    return start, start + timedelta(days=7)


def is_in_week(dt: datetime | None, week: str) -> bool:
    if dt is None:
        return False
    return current_week(dt) == week


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
