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
from app.models._common import NOW_UTC

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.user import User


class Result(Base):
    """Một lần làm bài của một sinh viên. Làm lại bài tạo dòng mới (attempt_no tăng)."""

    __tablename__ = "results"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "assessment_id", "attempt_no", name="uq_results_user_assessment_attempt"
        ),
        CheckConstraint("attempt_no >= 1", name="attempt_no_min"),
        CheckConstraint("score >= 0", name="score_min"),
        CheckConstraint("wrong_count >= 0", name="wrong_count_min"),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0", name="duration_seconds_min"
        ),
        CheckConstraint("started_at IS NULL OR started_at <= completed_at", name="time_order"),
        Index("idx_results_user_completed", "user_id", "completed_at"),
        Index("idx_results_assessment", "assessment_id"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"))
    attempt_no: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    score: Mapped[float] = mapped_column(REAL)  # điểm thô; app: <= assessments.max_score
    wrong_count: Mapped[int] = mapped_column(Integer)  # app: <= assessments.total_questions
    started_at: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[str] = mapped_column(Text)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(Text, server_default=NOW_UTC)

    user: Mapped[User] = relationship(back_populates="results")
    assessment: Mapped[Assessment] = relationship(back_populates="results")
