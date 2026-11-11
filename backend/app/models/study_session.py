from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._common import NOW_UTC, in_values
from app.models.enums import SessionSource

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.user import User


class StudySession(Base):
    """Phiên học (FR09). Giao diện ghi nhận làm sau MVP, bảng và dữ liệu mô phỏng có sẵn."""

    __tablename__ = "study_sessions"
    __table_args__ = (
        CheckConstraint(
            "duration_seconds > 0 AND duration_seconds <= 86400", name="duration_range"
        ),
        CheckConstraint(in_values("source", SessionSource), name="source"),
        Index("idx_sessions_user_started", "user_id", "started_at"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    # NULL = học chung, không theo chủ đề cụ thể. App: chủ đề phải thuộc course_id.
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    started_at: Mapped[str] = mapped_column(Text)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(
        Text, default=SessionSource.SEED.value, server_default=SessionSource.SEED.value
    )
    created_at: Mapped[str] = mapped_column(Text, server_default=NOW_UTC)

    user: Mapped[User] = relationship(back_populates="study_sessions")
    course: Mapped[Course] = relationship(back_populates="study_sessions")
