"""Cấu hình môi trường Alembic cho StudyLens.

- URL DB lấy từ `app.core.config` (cùng nguồn với ứng dụng), có thể ghi đè bằng
  `config.set_main_option("sqlalchemy.url", ...)` (test dùng cách này).
- `render_as_batch=True`: SQLite không hỗ trợ ALTER TABLE đầy đủ, Alembic phải tạo lại bảng.
- Migration chạy với khóa ngoại TẮT (xem `create_db_engine`), tránh ON DELETE CASCADE
  xóa nhầm dữ liệu bảng con khi bảng cha bị tạo lại.
"""

from logging.config import fileConfig

from alembic import context
from app.core.config import settings
from app.core.database import Base, create_db_engine

# Import đủ model để Base.metadata biết hết các bảng.
import app.models  # noqa: F401  # isort: skip

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _database_url() -> str:
    return config.get_main_option("sqlalchemy.url") or settings.database_url


def run_migrations_offline() -> None:
    """Sinh SQL ra màn hình mà không kết nối DB (`alembic upgrade head --sql`)."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_db_engine(_database_url(), enforce_foreign_keys=False)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
