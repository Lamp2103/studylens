import os
import re
import subprocess
import sys
from datetime import datetime, time

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.core.config import BASE_DIR
from app.core.database import create_db_engine
from app.core.security import verify_password
from app.core.time import to_iso
from app.models import (
    Assessment,
    Course,
    Recommendation,
    Result,
    StudySession,
    Topic,
    User,
)
from app.seed.seed_data import (
    CURRENT_WEEK,
    DEFAULT_PASSWORD,
    DEMO_COURSE_CODE,
    PROFILES,
    TOTAL_WEEKS,
    VN_TZ,
    SeedError,
    seed_demo_data,
)
from tests import reference_metrics as ref

# Thứ Năm của tuần 5 (môn bắt đầu thứ Hai 2026-10-12).
NOW = datetime(2026, 11, 12, 18, 0, tzinfo=VN_TZ)
ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


@pytest.fixture
def seeded(session):
    summary = seed_demo_data(session, now=NOW)
    session.commit()
    return summary


def _metrics(session, username, today=None):
    today = today or NOW.date()
    user = session.scalar(select(User).where(User.username == username))
    course = session.scalar(select(Course).where(Course.code == DEMO_COURSE_CODE))
    return ref.compute(session, user.id, course, today)


def _count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def _dump(session):
    """Ảnh chụp dữ liệu không phụ thuộc id (id tăng dần qua các lần reset)."""
    results = session.execute(
        select(
            User.username,
            Assessment.title,
            Result.attempt_no,
            Result.score,
            Result.wrong_count,
            Result.started_at,
            Result.completed_at,
            Result.duration_seconds,
        )
        .join(User, User.id == Result.user_id)
        .join(Assessment, Assessment.id == Result.assessment_id)
        .order_by(User.username, Assessment.title, Result.attempt_no)
    ).all()
    sessions = session.execute(
        select(
            User.username,
            StudySession.started_at,
            StudySession.duration_seconds,
            StudySession.topic_id.is_(None),
        )
        .join(User, User.id == StudySession.user_id)
        .order_by(User.username, StudySession.started_at)
    ).all()
    return [tuple(r) for r in results], [tuple(r) for r in sessions]


def _scores(session):
    return session.execute(
        select(User.username, Assessment.title, Result.attempt_no, Result.score, Result.wrong_count)
        .join(User, User.id == Result.user_id)
        .join(Assessment, Assessment.id == Result.assessment_id)
        .order_by(User.username, Assessment.title, Result.attempt_no)
    ).all()


# ------------------------------------------------------------------ quy mô theo yêu cầu W1-B4
def test_scale_matches_requirements(session, seeded):
    assert _count(session, Course) == 1  # 1 môn
    assert 5 <= _count(session, Topic) <= 6  # 5-6 chủ đề
    assert 3 <= _count(session, User) <= 5  # 3-5 sinh viên
    course = session.scalar(select(Course))
    assert 4 <= course.total_weeks <= 6  # 4-6 tuần
    assert seeded.counts == {
        "courses": 1,
        "topics": 6,
        "assessments": 18,
        "users": 5,
        "results": _count(session, Result),
        "study_sessions": _count(session, StudySession),
    }
    weeks_with_results = set(
        session.scalars(
            select(Assessment.week_no)
            .join(Result, Result.assessment_id == Assessment.id)
            .distinct()
        )
    )
    assert weeks_with_results == {1, 2, 3, 4, 5}


def test_everything_is_marked_as_synthetic_test_data(session, seeded):
    assert all(u.is_synthetic for u in session.scalars(select(User)))
    assert "MÔ PHỎNG" in session.scalar(select(Course.description))


def test_demo_accounts_can_log_in_with_the_documented_password(session, seeded):
    assert seeded.password == DEFAULT_PASSWORD
    for user in session.scalars(select(User)):
        assert user.password_hash.startswith("$2b$")
        assert verify_password(DEFAULT_PASSWORD, user.password_hash)
    assert [s[0] for s in seeded.students] == [p.username for p in PROFILES]


def test_current_week_is_week_5_and_week_6_is_not_yet_assigned(session, seeded):
    course = session.scalar(select(Course))
    assert ref.current_week(course, NOW.date()) == CURRENT_WEEK == 5
    assert course.total_weeks == TOTAL_WEEKS == 6
    assert seeded.current_week == 5 and seeded.start_date == "2026-10-12"
    future = session.scalars(select(Assessment).where(Assessment.week_no > CURRENT_WEEK)).all()
    assert len(future) == 1
    assert _count(session, Assessment) - len(future) == 17
    assert (
        session.scalar(
            select(func.count()).select_from(Result).where(Result.assessment_id == future[0].id)
        )
        == 0
    )


# ------------------------------------------------------------------ dữ liệu hợp lệ
def test_all_rows_respect_cross_table_rules_sqlite_cannot_check(session, seeded):
    rows = session.execute(
        select(Result, Assessment).join(Assessment, Assessment.id == Result.assessment_id)
    ).all()
    assert rows
    for r, a in rows:
        assert 0 <= r.score <= a.max_score
        assert 0 <= r.wrong_count <= a.total_questions
        assert 1 <= a.week_no <= TOTAL_WEEKS
    for s in session.scalars(select(StudySession)):
        assert s.source == "seed"
        topic = session.get(Topic, s.topic_id) if s.topic_id else None
        assert topic is None or topic.course_id == s.course_id


def test_score_and_wrong_count_are_consistent(session, seeded):
    for r, a in session.execute(select(Result, Assessment).join(Assessment)).all():
        correct = a.total_questions - r.wrong_count
        assert r.score == pytest.approx(correct * a.max_score / a.total_questions)


def test_two_score_scales_exist_so_percent_normalisation_is_exercised(session, seeded):
    assert set(session.scalars(select(Assessment.max_score))) == {10.0, 20.0}


@pytest.mark.parametrize(
    "now", [NOW, datetime(2026, 11, 9, 8, 0, tzinfo=VN_TZ)]
)  # thứ Năm, sáng thứ Hai
def test_no_timestamp_is_in_the_future_and_format_is_consistent(session, now):
    seed_demo_data(session, now=now)
    session.commit()
    limit = to_iso(now)
    for r in session.scalars(select(Result)):
        for value in (r.started_at, r.completed_at):
            assert ISO_Z.match(value), value
        assert r.started_at <= r.completed_at
        assert r.completed_at <= limit
    for s in session.scalars(select(StudySession)):
        assert ISO_Z.match(s.started_at)
        assert s.started_at <= limit  # chuỗi ISO cùng định dạng: so sánh chuỗi = so sánh thời gian


# ------------------------------------------------------------------ kết quả theo bộ quy tắc
def test_dataset_covers_every_case_of_the_rules(session, seeded):
    all_metrics = [_metrics(session, p.username) for p in PROFILES]
    labels = {t.label for m in all_metrics for t in m.topics.values()}
    assert labels == {"strong", "medium", "weak", "insufficient", "no_data"}
    assert {m.trend for m in all_metrics} >= {"up", "down", "stable"}
    assert session.scalar(select(func.max(Result.attempt_no))) == 2  # có làm lại bài


def test_sv01_improving_student(session, seeded):
    m = _metrics(session, "sv01")
    assert m.completion == (17, 17)
    assert m.trend == "up" and m.trend_delta >= ref.TREND_THRESHOLD
    assert m.topics[4].label == "strong" and m.topics[6].label == "strong"
    assert all(t.label != "weak" for t in m.topics.values())


def test_latest_attempt_is_the_one_that_counts(session, seeded):
    """sv01 làm lại 'Ngăn xếp - Bài tập 1': 50% rồi 70%. Chỉ lần 2 được tính."""
    user = session.scalar(select(User).where(User.username == "sv01"))
    a = session.scalar(
        select(Assessment).where(Assessment.title == "Ngăn xếp và hàng đợi – Bài tập 1")
    )
    attempts = session.scalars(
        select(Result)
        .where(Result.user_id == user.id, Result.assessment_id == a.id)
        .order_by(Result.attempt_no)
    ).all()
    assert [round(r.score / a.max_score * 100) for r in attempts] == [50, 70]
    assert attempts[0].completed_at < attempts[1].completed_at
    ((latest, _),) = [(r, x) for r, x in ref.latest_attempts(session, user.id) if x.id == a.id]
    assert latest.attempt_no == 2


def test_sv02_weak_and_declining_student(session, seeded):
    m = _metrics(session, "sv02")
    assert m.completion == (15, 17)
    assert m.trend == "down" and m.trend_delta <= -ref.TREND_THRESHOLD
    assert m.topics[4].label == "weak" and m.topics[5].label == "weak"
    assert m.topics[1].label == "strong"  # có cả chủ đề mạnh lẫn yếu
    weak_wrong = sum(m.topics[k].wrong_total for k in (4, 5)) / sum(
        m.topics[k].done for k in (4, 5)
    )
    strong_wrong = m.topics[1].wrong_total / m.topics[1].done
    assert weak_wrong > 2 * strong_wrong  # chủ đề yếu sai nhiều hơn hẳn


def test_sv03_strong_and_stable_student(session, seeded):
    m = _metrics(session, "sv03")
    assert m.completion == (17, 17)
    assert m.trend == "stable"
    assert {t.label for t in m.topics.values()} == {"strong"}  # không có gì để gợi ý ôn


def test_sv04_late_starter_has_missing_data(session, seeded):
    m = _metrics(session, "sv04")
    assert m.completion == (9, 17)
    assert m.topics[2].label == "no_data" and m.topics[2].avg_pct is None and m.topics[2].done == 0
    assert m.topics[1].label == "insufficient" and m.topics[1].done == 1
    assert m.topics[6].label == "insufficient" and m.topics[6].done == 1
    assert set(m.weekly_avg) == {3, 4, 5}  # không có dữ liệu tuần 1-2


def test_sv05_scores_sit_exactly_on_the_thresholds(session, seeded):
    m = _metrics(session, "sv05")
    assert m.completion == (17, 17)
    assert m.trend == "stable"
    assert m.topics[2].avg_pct == pytest.approx(75.0, abs=1e-9) and m.topics[2].label == "strong"
    assert m.topics[3].avg_pct == pytest.approx(50.0, abs=1e-9) and m.topics[3].label == "medium"
    # lần 1 chỉ 40% (sẽ là "yếu" nếu tính nhầm), lần 2 được 60%
    user = session.scalar(select(User).where(User.username == "sv05"))
    a = session.scalar(
        select(Assessment).where(Assessment.title == "Sắp xếp và tìm kiếm – Bài tập 1")
    )
    first, second = session.scalars(
        select(Result)
        .where(Result.user_id == user.id, Result.assessment_id == a.id)
        .order_by(Result.attempt_no)
    ).all()
    assert (first.score, second.score) == (4.0, 6.0)


def test_completion_only_counts_assignments_up_to_the_current_week(session, seeded):
    course = session.scalar(select(Course))
    assert ref.current_week(course, NOW.date()) == 5
    # Nếu "hôm nay" là tuần 6 thì có 18 bài đã giao, tiến độ đổi mẫu số.
    week6 = _metrics(session, "sv03", today=NOW.date().replace(day=19))
    assert week6.completion == (17, 18)


# ------------------------------------------------------------------ tính xác định
def test_same_inputs_give_identical_data_even_after_reset(session, seeded):
    first = _dump(session)
    seed_demo_data(session, now=NOW, reset=True)
    session.commit()
    assert _dump(session) == first


def test_different_rng_seed_gives_different_scores(session, seeded):
    before = _scores(session)
    seed_demo_data(session, now=NOW, rng_seed=7, reset=True)
    session.commit()
    assert _scores(session) != before


def test_scores_do_not_depend_on_the_run_date(session, seeded):
    """Đổi ngày chạy chỉ đổi mốc thời gian, không đổi điểm."""
    before = _scores(session)
    seed_demo_data(session, now=datetime(2026, 11, 9, 8, 0, tzinfo=VN_TZ), reset=True)
    session.commit()
    assert _scores(session) == before


# ------------------------------------------------------------------ chạy lại / reset
def test_seeding_twice_without_reset_is_refused_and_changes_nothing(session, seeded):
    before = _dump(session)
    with pytest.raises(SeedError, match="--reset"):
        seed_demo_data(session, now=NOW)
    session.rollback()
    assert _dump(session) == before and _count(session, Course) == 1


def test_reset_replaces_demo_data_but_keeps_real_accounts(session, seeded):
    real = User(
        username="that01", password_hash="x", display_name="Tài khoản thật", is_synthetic=False
    )
    session.add(real)
    demo = session.scalar(select(User).where(User.username == "sv01"))
    topic = session.scalar(select(Topic))
    session.add(
        Recommendation(
            user_id=demo.id,
            topic_id=topic.id,
            type="review_topic",
            rank=1,
            priority_score=1,
            reason_text="x",
            evidence_json={"reasons": [{"code": "low_average"}]},
        )
    )
    session.commit()

    seed_demo_data(session, now=NOW, reset=True)
    session.commit()

    assert _count(session, Course) == 1 and _count(session, Assessment) == 18
    assert _count(session, User) == 6  # 5 mô phỏng + 1 thật
    assert session.scalar(select(User).where(User.username == "that01")) is not None
    assert _count(session, Recommendation) == 0  # gợi ý cũ bị xóa theo


def test_refuses_when_a_real_user_already_owns_a_demo_username(session):
    session.add(User(username="SV01", password_hash="x", display_name="thật", is_synthetic=False))
    session.commit()
    with pytest.raises(SeedError, match="(?i)sv01"):
        seed_demo_data(session, now=NOW)


def test_clear_message_when_database_is_not_migrated(db_url):
    engine = create_db_engine(db_url)  # chưa chạy alembic
    with sessionmaker(bind=engine)() as s, pytest.raises(SeedError, match="alembic upgrade head"):
        seed_demo_data(s, now=NOW)
    engine.dispose()


def test_now_must_be_timezone_aware(session):
    with pytest.raises(ValueError):
        seed_demo_data(session, now=datetime.combine(NOW.date(), time(9, 0)))


# ------------------------------------------------------------------ dòng lệnh
def test_command_line_runs_with_a_non_utf8_terminal(migrated_engine, db_url):
    """Mô phỏng terminal Windows (không UTF-8): in tiếng Việt không được làm script sập."""
    env = {
        **os.environ,
        "DATABASE_URL": db_url,
        "BCRYPT_ROUNDS": "4",
        "LC_ALL": "C",
        "PYTHONUTF8": "0",
        "PYTHONCOERCECLOCALE": "0",
    }
    env.pop("PYTHONIOENCODING", None)

    def run(*args):
        return subprocess.run(
            [sys.executable, "-m", "app.seed.seed_data", "--today", "2026-11-12", *args],
            cwd=BASE_DIR,
            env=env,
            capture_output=True,
        )

    first = run()
    assert first.returncode == 0, first.stderr.decode("utf-8", "replace")
    out = first.stdout.decode("utf-8")
    assert "KHÔNG phải dữ liệu thật" in out and "tuần 5/6" in out
    assert "sv01" in out and DEFAULT_PASSWORD in out

    again = run()
    assert again.returncode == 1
    assert "--reset" in again.stderr.decode("utf-8")

    assert run("--reset").returncode == 0
