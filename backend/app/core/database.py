"""Kết nối cơ sở dữ liệu (SQLAlchemy 2.x, đồng bộ).

- `Base`: lớp cha cho các model (W1-B3 sẽ khai báo 7 bảng kế thừa lớp này).
- `engine`, `SessionLocal`: kết nối và phiên làm việc.
- `get_db`: dependency của FastAPI, mỗi request một phiên, tự đóng khi xong.
"""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# Đặt tên ràng buộc theo quy ước cố định. Bắt buộc với SQLite: Alembic sửa bảng bằng cách
# tạo lại bảng ("batch mode") và chỉ xử lý được ràng buộc có tên.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Lớp cha của mọi model SQLAlchemy."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _ensure_sqlite_dir(url: str) -> None:
    """Tạo thư mục chứa file SQLite nếu chưa có (ví dụ `data/`)."""
    database = make_url(url).database
    if database and database != ":memory:":
        Path(database).parent.mkdir(parents=True, exist_ok=True)


def create_db_engine(url: str, *, enforce_foreign_keys: bool = True) -> Engine:
    """Tạo engine.

    `enforce_foreign_keys=False` chỉ dùng khi chạy migration Alembic: xóa/tạo lại bảng
    trong lúc khóa ngoại bật sẽ kích hoạt ON DELETE CASCADE và làm mất dữ liệu bảng con.
    """
    connect_args: dict = {}
    if _is_sqlite(url):
        _ensure_sqlite_dir(url)
        # FastAPI chạy endpoint đồng bộ trong thread pool, nên phải tắt kiểm tra thread.
        connect_args["check_same_thread"] = False

    engine = create_engine(url, connect_args=connect_args)

    if _is_sqlite(url) and enforce_foreign_keys:

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record) -> None:
            # SQLite mặc định TẮT khóa ngoại. Bắt buộc bật ở MỖI kết nối,
            # nếu không ON DELETE CASCADE và kiểm tra khóa ngoại sẽ không chạy.
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = create_db_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
