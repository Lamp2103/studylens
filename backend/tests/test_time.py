from datetime import UTC, datetime, timedelta, timezone

from app.core.time import to_iso, utc_now_iso


def test_to_iso_format_and_utc_conversion():
    assert to_iso(datetime(2026, 11, 9, 8, 30, tzinfo=UTC)) == "2026-11-09T08:30:00.000Z"
    vn = timezone(timedelta(hours=7))
    assert to_iso(datetime(2026, 11, 9, 15, 30, 0, 123000, tzinfo=vn)) == "2026-11-09T08:30:00.123Z"


def test_naive_datetime_is_treated_as_utc():
    assert to_iso(datetime(2026, 1, 2, 3, 4, 5)) == "2026-01-02T03:04:05.000Z"


def test_utc_now_iso_sorts_like_time():
    a = utc_now_iso()
    b = to_iso(datetime.now(UTC) + timedelta(seconds=1))
    assert a.endswith("Z") and a < b
