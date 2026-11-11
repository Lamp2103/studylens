from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.course import Course


class Topic(Base):
    """Chủ đề kiến thức của một môn."""

    __tablename__ = "topics"
    __table_args__ = (
        UniqueConstraint("course_id", "name", name="uq_topics_course_name"),
        UniqueConstraint("course_id", "order_no", name="uq_topics_course_order"),
        CheckConstraint("order_no >= 1", name="order_no_min"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    order_no: Mapped[int] = mapped_column(Integer)  # thứ tự hiển thị

    course: Mapped[Course] = relationship(back_populates="topics")
    assessments: Mapped[list[Assessment]] = relationship(
        back_populates="topic", cascade="all, delete-orphan", passive_deletes=True
    )
