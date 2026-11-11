"""Các tập giá trị cố định. Là nguồn duy nhất cho cả CHECK trong DB lẫn schema Pydantic sau này."""

from enum import StrEnum


class Role(StrEnum):
    STUDENT = "student"
    ADMIN = "admin"


class AssessmentType(StrEnum):
    EXERCISE = "exercise"
    QUIZ = "quiz"
    EXAM = "exam"


class SessionSource(StrEnum):
    SEED = "seed"
    MANUAL = "manual"
    TIMER = "timer"


class RecommendationType(StrEnum):
    REVIEW_TOPIC = "review_topic"
    RETRY_ASSESSMENT = "retry_assessment"
    PRACTICE_MORE = "practice_more"


class RecommendationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    COMPLETED = "completed"
