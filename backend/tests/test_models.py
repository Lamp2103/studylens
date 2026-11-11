import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import (
    Assessment,
    Course,
    Recommendation,
    Result,
    StudySession,
    Topic,
    User,
)

EVIDENCE = {
    "reasons": [{"code": "low_average", "detail": "Điểm TB 45%, thấp nhất"}],
    "metrics": {"avg_pct": 45.0, "wrong_total": 11},
}


@pytest.fixture
def base(session):
    """Một sinh viên, một môn, hai chủ đề, hai bài."""
    user = User(username="sv01", password_hash="x", display_name="Sinh viên 01")
    course = Course(code="DEMO101", name="Môn demo", start_date="2026-11-09", total_weeks=6)
    course.topics = [Topic(name="Chủ đề A", order_no=1), Topic(name="Chủ đề B", order_no=2)]
    session.add_all([user, course])
    session.flush()
    a1 = Assessment(topic_id=course.topics[0].id, title="A-BT1", week_no=1, total_questions=10)
    a2 = Assessment(topic_id=course.topics[1].id, title="B-BT1", week_no=1, total_questions=10)
    session.add_all([a1, a2])
    session.commit()
    return {"user": user, "course": course, "a1": a1, "a2": a2}


def _result(base, assessment="a1", **kw):
    data = {
        "user_id": base["user"].id,
        "assessment_id": base[assessment].id,
        "score": 5,
        "wrong_count": 5,
        "completed_at": "2026-11-10T08:00:00.000Z",
    }
    return Result(**{**data, **kw})


def _rec(base, **kw):
    data = {
        "user_id": base["user"].id,
        "topic_id": base["course"].topics[0].id,
        "type": "review_topic",
        "rank": 1,
        "priority_score": 80,
        "reason_text": "Ôn lại chủ đề A",
        "evidence_json": EVIDENCE,
    }
    return Recommendation(**{**data, **kw})


# ---------------------------------------------------------------- giá trị mặc định
def test_defaults(session, base):
    session.add_all([_result(base), _rec(base)])
    session.commit()
    user, assessment = base["user"], base["a1"]
    session.refresh(user)
    assert (user.role, user.is_synthetic, user.is_active) == ("student", True, True)
    assert user.created_at.endswith("Z") and "T" in user.created_at
    assert assessment.type == "exercise" and assessment.max_score == 10
    result = session.scalars(select(Result)).one()
    assert result.attempt_no == 1
    rec = session.scalars(select(Recommendation)).one()
    assert (rec.status, rec.is_current) == ("pending", True)
    assert rec.generated_at.endswith("Z")


def test_evidence_json_roundtrip_keeps_vietnamese(session, base):
    session.add(_rec(base))
    session.commit()
    session.expire_all()
    rec = session.scalars(select(Recommendation)).one()
    assert rec.evidence_json == EVIDENCE
    assert isinstance(rec.evidence_json, dict)


def test_topics_are_ordered_by_order_no(session, base):
    session.expire_all()
    assert [t.name for t in base["course"].topics] == ["Chủ đề A", "Chủ đề B"]


# ---------------------------------------------------------------- ràng buộc
def test_username_is_unique_case_insensitive(session, base):
    session.add(User(username="SV01", password_hash="x", display_name="trùng"))
    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"score": -1},
        {"wrong_count": -1},
        {"duration_seconds": -5},
        {"attempt_no": 0},
        {"started_at": "2026-11-11T00:00:00.000Z"},  # sau completed_at
    ],
)
def test_result_check_constraints(session, base, kwargs):
    session.add(_result(base, **kwargs))
    with pytest.raises(IntegrityError):
        session.commit()


def test_same_attempt_cannot_be_stored_twice_but_retry_can(session, base):
    session.add(_result(base))
    session.commit()
    session.add(_result(base))  # trùng attempt_no = 1
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.add(_result(base, attempt_no=2, score=7, wrong_count=3))
    session.commit()
    assert len(session.scalars(select(Result)).all()) == 2


def test_enum_checks(session, base):
    for obj in (
        _rec(base, status="bad"),
        _rec(base, type="bad"),
        StudySession(
            user_id=base["user"].id,
            course_id=base["course"].id,
            started_at="2026-11-10T07:00:00.000Z",
            duration_seconds=60,
            source="bad",
        ),
    ):
        session.add(obj)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_study_session_duration_range(session, base):
    for seconds in (0, 86401):
        session.add(
            StudySession(
                user_id=base["user"].id,
                course_id=base["course"].id,
                started_at="2026-11-10T07:00:00.000Z",
                duration_seconds=seconds,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


@pytest.mark.parametrize(
    "evidence",
    [{"reasons": []}, {"metrics": {}}, {}, {"reasons": "low_average"}, {"reasons": None}],
)
def test_recommendation_requires_at_least_one_reason(session, base, evidence):
    session.add(_rec(base, evidence_json=evidence))
    with pytest.raises(IntegrityError):
        session.commit()


def test_only_one_current_recommendation_per_user_topic_type(session, base):
    session.add(_rec(base))
    session.commit()
    session.add(_rec(base, rank=2))  # trùng (user, topic, type, assessment NULL), cùng is_current
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    # Đúng quy trình tính lại: đặt gợi ý cũ is_current = False rồi thêm gợi ý mới.
    old = session.scalars(select(Recommendation)).one()
    old.is_current = False
    session.add(_rec(base, priority_score=70))
    session.commit()
    assert len(session.scalars(select(Recommendation)).all()) == 2


def test_different_assessment_is_a_different_recommendation(session, base):
    session.add_all([_rec(base), _rec(base, assessment_id=base["a1"].id, type="retry_assessment")])
    session.commit()


# ---------------------------------------------------------------- khóa ngoại
def test_foreign_keys_are_enforced(session, base):
    session.add(_result(base, user_id=9999))
    with pytest.raises(IntegrityError):
        session.commit()


def test_deleting_user_cascades(session, base):
    session.add_all(
        [
            _result(base),
            _rec(base),
            StudySession(
                user_id=base["user"].id,
                course_id=base["course"].id,
                started_at="2026-11-10T07:00:00.000Z",
                duration_seconds=3600,
            ),
        ]
    )
    session.commit()
    session.delete(base["user"])
    session.commit()
    for model in (Result, Recommendation, StudySession):
        assert session.scalars(select(model)).all() == []
    # dữ liệu giảng dạy không bị ảnh hưởng
    assert len(session.scalars(select(Assessment)).all()) == 2


def test_deleting_topic_sets_null_on_study_session_and_cascades_assessments(session, base):
    topic = base["course"].topics[0]
    session.add(
        StudySession(
            user_id=base["user"].id,
            course_id=base["course"].id,
            topic_id=topic.id,
            started_at="2026-11-10T07:00:00.000Z",
            duration_seconds=600,
        )
    )
    session.add(_result(base))
    session.commit()
    session.delete(topic)
    session.commit()
    assert session.scalars(select(StudySession)).one().topic_id is None
    assert session.scalars(select(Result)).all() == []  # bài bị xóa kéo theo kết quả


def test_deleting_assessment_sets_null_on_recommendation(session, base):
    session.add(_rec(base, assessment_id=base["a1"].id, type="retry_assessment"))
    session.commit()
    session.delete(base["a1"])
    session.commit()
    assert session.scalars(select(Recommendation)).one().assessment_id is None
