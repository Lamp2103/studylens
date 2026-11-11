"""Cấu hình ứng dụng, đọc từ biến môi trường hoặc file `.env`.

Mọi giá trị cấu hình đi qua `settings` để không rải hằng số khắp mã nguồn.
Muốn đổi giá trị: sửa `.env` (xem `.env.example`), không sửa trực tiếp ở đây.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Thư mục gốc của backend (chứa app/, data/, .env)
BASE_DIR = Path(__file__).resolve().parents[2]

_DEV_SECRET = "dev-only-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "StudyLens API"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"

    # Đường dẫn tuyệt đối để chạy từ thư mục nào cũng trỏ đúng file DB.
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'studylens.db'}"

    # Địa chỉ frontend được phép gọi API (Vite dev server mặc định cổng 5173).
    # Trong .env viết dạng JSON: CORS_ORIGINS=["http://localhost:5173"]
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Dùng cho JWT ở tuần 2 (FR01). Chưa dùng trong khung này.
    secret_key: str = _DEV_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Độ khó băm mật khẩu bcrypt. 12 là mức khuyến nghị; test dùng 4 cho nhanh.
    bcrypt_rounds: int = Field(default=12, ge=4, le=16)

    @model_validator(mode="after")
    def _reject_default_secret_in_production(self) -> "Settings":
        if self.environment == "production" and self.secret_key == _DEV_SECRET:
            raise ValueError("SECRET_KEY phải được đặt riêng khi ENVIRONMENT=production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
