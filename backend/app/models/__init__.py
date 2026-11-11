"""Import đủ mọi model để `Base.metadata` biết hết các bảng (Alembic và test cần điều này)."""

from app.models.assessment import Assessment
from app.models.course import Course
from app.models.enums import (
    AssessmentType,
    RecommendationStatus,
    RecommendationType,
    Role,
    SessionSource,
)
from app.models.recommendation import Recommendation
from app.models.result import Result
from app.models.study_session import StudySession
from app.models.topic import Topic
from app.models.user import User

__all__ = [
    "Assessment",
    "AssessmentType",
    "Course",
    "Recommendation",
    "RecommendationStatus",
    "RecommendationType",
    "Result",
    "Role",
    "SessionSource",
    "StudySession",
    "Topic",
    "User",
]
