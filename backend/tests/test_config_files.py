from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]

# Các file do công cụ bên ngoài đọc bằng bảng mã mặc định của hệ điều hành (cp1252 trên Windows),
# nên chỉ được chứa ký tự ASCII. Chú thích tiếng Việt để trong file .py (luôn đọc bằng UTF-8).
ASCII_ONLY = [
    "alembic.ini",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    ".env.example",
    ".python-version",
]


@pytest.mark.parametrize("name", ASCII_ONLY)
def test_config_file_is_ascii_only(name):
    data = (BACKEND / name).read_bytes()
    bad = [n for n, line in enumerate(data.split(b"\n"), 1) if any(b > 127 for b in line)]
    assert not bad, (
        f"{name}: ký tự không phải ASCII ở dòng {bad}. Hãy viết chú thích bằng tiếng Anh."
    )
