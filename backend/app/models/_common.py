"""Thành phần dùng chung cho các model."""

import json
from enum import StrEnum

from sqlalchemy import Text, TypeDecorator, text

# Giá trị mặc định cho cột thời gian: chuỗi ISO 8601 UTC, khớp với app.core.time.to_iso().
NOW_UTC = text("(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))")


def in_values(column: str, enum_cls: type[StrEnum]) -> str:
    """Sinh biểu thức CHECK: `role IN ('student', 'admin')`."""
    values = ", ".join(f"'{member.value}'" for member in enum_cls)
    return f"{column} IN ({values})"


class JSONText(TypeDecorator):
    """Lưu dict/list Python thành chuỗi JSON trong cột TEXT (đọc ra lại thành dict/list).

    Dùng thay `sqlalchemy.JSON` để cột trong SQLite vẫn có kiểu TEXT và CHECK(json_valid) hoạt động.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, _dialect):
        return None if value is None else json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value, _dialect):
        return None if value is None else json.loads(value)
