"""Băm và kiểm tra mật khẩu (bcrypt). Tuần 2 sẽ thêm JWT ở đây (FR01).

Dùng thư viện `bcrypt` trực tiếp. Không lưu và không ghi log mật khẩu thô (NFR06).
"""

import bcrypt

from app.core.config import settings

# bcrypt chỉ xử lý tối đa 72 byte đầu của mật khẩu. Từ chối thay vì âm thầm cắt bớt.
MAX_PASSWORD_BYTES = 72


def hash_password(password: str, *, rounds: int | None = None) -> str:
    raw = password.encode("utf-8")
    if len(raw) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Mật khẩu dài quá {MAX_PASSWORD_BYTES} byte")
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds if rounds is None else rounds)
    return bcrypt.hashpw(raw, salt).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:  # mật khẩu quá dài hoặc hash hỏng: coi là không khớp
        return False
