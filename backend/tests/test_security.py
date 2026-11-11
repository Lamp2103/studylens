import pytest

from app.core.security import MAX_PASSWORD_BYTES, hash_password, verify_password


def test_hash_and_verify():
    h = hash_password("Demo@123")
    assert h.startswith("$2b$04$")  # conftest đặt BCRYPT_ROUNDS=4
    assert "Demo@123" not in h
    assert verify_password("Demo@123", h)
    assert not verify_password("demo@123", h)


def test_each_hash_has_its_own_salt():
    assert hash_password("x") != hash_password("x")


def test_unicode_password():
    h = hash_password("mật-khẩu-Việt-123")
    assert verify_password("mật-khẩu-Việt-123", h)


def test_too_long_password_is_rejected_not_truncated():
    with pytest.raises(ValueError):
        hash_password("a" * (MAX_PASSWORD_BYTES + 1))
    assert not verify_password("a" * 100, hash_password("a" * 72))


def test_broken_hash_is_not_a_match():
    assert not verify_password("x", "not-a-bcrypt-hash")
