from datetime import datetime

import pytest

from app.time import LOCAL_TZ, week_bounds


def test_week_bounds_returns_local_monday_and_exclusive_next_monday() -> None:
    start, end = week_bounds("2026-W29")

    assert start == datetime(2026, 7, 13, tzinfo=LOCAL_TZ)
    assert end == datetime(2026, 7, 20, tzinfo=LOCAL_TZ)


@pytest.mark.parametrize("week", ["2026-W00", "2026-W54", "2026-29", "W29"])
def test_week_bounds_rejects_invalid_iso_weeks(week: str) -> None:
    with pytest.raises(ValueError):
        week_bounds(week)
