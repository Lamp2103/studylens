from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._common import NOW_UTC

if TYPE_CHECKING:
    from app.models.study_session import StudySession
    from app.models.topic import Topic


class Course(Base):
    """Môn học."""

    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("total_weeks > 0", name="total_weeks_positive"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[str] = mapped_column(Text)  # YYYY-MM-DD, ngày đầu tuần 1
    total_weeks: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(Text, server_default=NOW_UTC)

    topics: Mapped[list[Topic]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Topic.order_no",
    )
    study_sessions: Mapped[list[StudySession]] = relationship(
        back_populates="course", cascade="all, delete-orphan", passive_deletes=True
    )
