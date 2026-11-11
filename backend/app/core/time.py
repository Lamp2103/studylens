"""Định dạng thời gian thống nhất cho toàn hệ thống.

Mọi mốc thời gian lưu trong DB là chuỗi ISO 8601 UTC kết thúc bằng `Z`, ví dụ
`2026-11-09T08:30:00.000Z`. Dùng MỘT định dạng duy nhất để so sánh chuỗi cho kết quả
đúng thứ tự thời gian (không trộn `Z` với `+00:00`).
"""

from datetime import UTC, datetime


def to_iso(value: datetime) -> str:
    """Chuyển datetime (có hoặc không có múi giờ; không có thì coi là UTC) sang chuỗi lưu DB."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    utc = value.astimezone(UTC)
    return f"{utc:%Y-%m-%dT%H:%M:%S}.{utc.microsecond // 1000:03d}Z"


def utc_now_iso() -> str:
    return to_iso(datetime.now(UTC))
