from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    REAL,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._common import NOW_UTC, JSONText, in_values
from app.models.enums import RecommendationStatus, RecommendationType

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.topic import Topic
    from app.models.user import User


class Recommendation(Base):
    """Gợi ý ôn tập (FR05, FR06; `status` phục vụ FR11).

    Mỗi lần tính lại, gợi ý cũ đặt is_current = False, gợi ý mới is_current = True.
    `evidence_json` giữ số liệu làm căn cứ để kiểm chứng lý do (NFR05), dạng:
        {"reasons": [{"code": "low_average", "detail": "..."}],
         "metrics": {"avg_pct": 45.0, "wrong_total": 11, "trend_delta": -30.0}}
    """

    __tablename__ = "recommendations"
    __table_args__ = (
        CheckConstraint(in_values("type", RecommendationType), name="type"),
        CheckConstraint("rank >= 1", name="rank_min"),
        CheckConstraint("priority_score >= 0", name="priority_score_min"),
        CheckConstraint(
            "CASE WHEN json_valid(evidence_json) "
            "THEN COALESCE(json_array_length(evidence_json, '$.reasons'), 0) >= 1 "
            "ELSE 0 END",
            name="evidence_has_reason",
        ),
        CheckConstraint(in_values("status", RecommendationStatus), name="status"),
        Index("idx_recs_user_current_rank", "user_id", "is_current", "rank"),
        # Mỗi sinh viên chỉ có một gợi ý hiện hành cho cùng (chủ đề, loại, bài).
        Index(
            "uq_recs_current",
            "user_id",
            "topic_id",
            "type",
            text("COALESCE(assessment_id, 0)"),
            unique=True,
            sqlite_where=text("is_current = 1"),
        ),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    # NULL = gợi ý cả chủ đề
    assessment_id: Mapped[int | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="SET NULL")
    )
    type: Mapped[str] = mapped_column(Text)
    rank: Mapped[int] = mapped_column(Integer)  # 1 = ưu tiên cao nhất
    priority_score: Mapped[float] = mapped_column(REAL)
    reason_text: Mapped[str] = mapped_column(Text)  # câu giải thích hiển thị cho sinh viên
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSONText)
    resource_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Text,
        default=RecommendationStatus.PENDING.value,
        server_default=RecommendationStatus.PENDING.value,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean(create_constraint=True, name="is_current_bool"),
        default=True,
        server_default=text("1"),
    )
    generated_at: Mapped[str] = mapped_column(Text, server_default=NOW_UTC)
    status_updated_at: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="recommendations")
    topic: Mapped[Topic] = relationship()
    assessment: Mapped[Assessment | None] = relationship()
