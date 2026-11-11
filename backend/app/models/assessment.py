from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    REAL,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._common import NOW_UTC, in_values
from app.models.enums import AssessmentType

if TYPE_CHECKING:
    from app.models.result import Result
    from app.models.topic import Topic


class Assessment(Base):
    """Bài tập / quiz / bài kiểm tra. Mỗi bài thuộc đúng một chủ đề."""

    __tablename__ = "assessments"
    __table_args__ = (
        UniqueConstraint("topic_id", "title", name="uq_assessments_topic_title"),
        CheckConstraint(in_values("type", AssessmentType), name="type"),
        CheckConstraint("week_no >= 1", name="week_no_min"),
        CheckConstraint("total_questions > 0", name="total_questions_positive"),
        CheckConstraint("max_score > 0", name="max_score_positive"),
        Index("idx_assessments_topic_week", "topic_id", "week_no"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(
        Text, default=AssessmentType.EXERCISE.value, server_default=AssessmentType.EXERCISE.value
    )
    week_no: Mapped[int] = mapped_column(Integer)  # tuần học của bài (FR07); app: <= total_weeks
    total_questions: Mapped[int] = mapped_column(Integer)
    max_score: Mapped[float] = mapped_column(REAL, default=10.0, server_default=text("10"))
    due_date: Mapped[str | None] = mapped_column(Text)  # YYYY-MM-DD
    created_at: Mapped[str] = mapped_column(Text, server_default=NOW_UTC)

    topic: Mapped[Topic] = relationship(back_populates="assessments")
    results: Mapped[list[Result]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", passive_deletes=True
    )
