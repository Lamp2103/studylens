from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._common import NOW_UTC, in_values
from app.models.enums import Role

if TYPE_CHECKING:
    from app.models.recommendation import Recommendation
    from app.models.result import Result
    from app.models.study_session import StudySession


class User(Base):
    """Tài khoản sinh viên (FR01, FR12)."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(in_values("role", Role), name="role"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(Text(collation="NOCASE"), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)  # bcrypt, không bao giờ lưu mật khẩu thô
    display_name: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(
        Text, default=Role.STUDENT.value, server_default=Role.STUDENT.value
    )
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean(create_constraint=True, name="is_synthetic_bool"),
        default=True,
        server_default=text("1"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean(create_constraint=True, name="is_active_bool"),
        default=True,
        server_default=text("1"),
    )
    created_at: Mapped[str] = mapped_column(Text, server_default=NOW_UTC)
    last_login_at: Mapped[str | None] = mapped_column(Text)

    results: Mapped[list[Result]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    study_sessions: Mapped[list[StudySession]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    recommendations: Mapped[list[Recommendation]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
