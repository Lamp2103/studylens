import os
import tempfile
from pathlib import Path

# Phải đặt TRƯỚC khi import app để test dùng DB tạm, không đụng data/studylens.db.
_tmp_dir = tempfile.mkdtemp(prefix="studylens-test-")
os.environ["ENVIRONMENT"] = "test"
os.environ["BCRYPT_ROUNDS"] = "4"  # băm mật khẩu nhanh trong test
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp_dir) / 'test.db'}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fixtures cho test model / migration: mỗi test một DB SQLite riêng, tạo bằng Alembic.
# ---------------------------------------------------------------------------
from alembic.config import Config  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from alembic import command  # noqa: E402
from app.core.config import BASE_DIR  # noqa: E402
from app.core.database import create_db_engine  # noqa: E402


def alembic_config(url: str) -> Config:
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture
def db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def migrated_engine(db_url):
    command.upgrade(alembic_config(db_url), "head")
    engine = create_db_engine(db_url)  # khóa ngoại BẬT, giống ứng dụng thật
    yield engine
    engine.dispose()


@pytest.fixture
def session(migrated_engine):
    with sessionmaker(bind=migrated_engine, autoflush=False, expire_on_commit=False)() as s:
        yield s
