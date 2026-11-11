"""Sinh dữ liệu MÔ PHỎNG cho StudyLens (W1-B4).

Toàn bộ dữ liệu do script này tạo ra là dữ liệu thử nghiệm, KHÔNG phải dữ liệu học tập thật:
tài khoản gắn cờ `users.is_synthetic = 1`, mô tả môn học ghi rõ như vậy (NFR07).

Cách chạy (từ thư mục backend/, sau khi đã `alembic upgrade head`):

    python -m app.seed.seed_data               # tạo dữ liệu (từ chối nếu đã có)
    python -m app.seed.seed_data --reset       # xóa dữ liệu mô phỏng cũ rồi tạo lại
    python -m app.seed.seed_data --today 2026-11-12 --seed 7

Dữ liệu được thiết kế để chạm TẤT CẢ các trường hợp trong bộ quy tắc tính chỉ số
(xem docs/03-api/seed-data-design.md):

  * "Tuần hiện tại" luôn là tuần 5/6 của môn, nên có một bài chưa giao (tuần 6).
  * Có chủ đề mạnh / trung bình / yếu, có điểm nằm đúng ngưỡng 75% và 50%.
  * Có chủ đề "chưa đủ dữ liệu" (< 2 bài) và "chưa có dữ liệu" (0 bài).
  * Có xu hướng tăng, giảm, ổn định; có sinh viên làm lại bài (lần gần nhất mới được tính).
  * Hai loại bài có thang điểm khác nhau (10 và 20) để kiểm tra việc quy đổi ra phần trăm.

Dữ liệu xác định: cùng `--seed` và cùng `--today` luôn cho cùng kết quả. Mỗi (sinh viên, bài)
dùng bộ sinh số ngẫu nhiên riêng, nên điểm không đổi khi thêm/bớt bài khác hoặc đổi ngày chạy.

Script không tạo bản ghi `recommendations`: gợi ý do bộ gợi ý (FR05) sinh ra từ dữ liệu này.
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta, timezone

from sqlalchemy import delete, inspect, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.core.time import to_iso
from app.models import (
    Assessment,
    AssessmentType,
    Course,
    Result,
    Role,
    SessionSource,
    StudySession,
    Topic,
    User,
)

VN_TZ = timezone(timedelta(hours=7))  # sinh viên ở Việt Nam; DB lưu UTC

DEMO_COURSE_CODE = "DEMO101"
DEFAULT_PASSWORD = "Demo@123"
DEFAULT_RNG_SEED = 2026
TOTAL_WEEKS = 6
CURRENT_WEEK = 5  # "tuần hiện tại" luôn là tuần 5: bài tuần 6 chưa giao

# ---------------------------------------------------------------------------------------
# Môn học, chủ đề, lịch bài tập
# ---------------------------------------------------------------------------------------
COURSE_NAME = "Cấu trúc dữ liệu và giải thuật"
COURSE_DESCRIPTION = (
    "DỮ LIỆU MÔ PHỎNG phục vụ thử nghiệm StudyLens, không phải dữ liệu học tập thật."
)

TOPICS: list[tuple[str, str]] = [
    ("Mảng và chuỗi", "Thao tác cơ bản trên mảng một chiều, hai chiều và chuỗi ký tự."),
    ("Danh sách liên kết", "Danh sách liên kết đơn, đôi và các thao tác thêm, xóa, đảo ngược."),
    ("Ngăn xếp và hàng đợi", "Cài đặt và ứng dụng ngăn xếp, hàng đợi."),
    ("Cây nhị phân", "Cây nhị phân, duyệt cây, cây tìm kiếm nhị phân."),
    ("Đồ thị", "Biểu diễn đồ thị, duyệt BFS/DFS, đường đi ngắn nhất."),
    ("Sắp xếp và tìm kiếm", "Các thuật toán sắp xếp, tìm kiếm nhị phân và độ phức tạp."),
]

# Mỗi chủ đề có 3 bài, giao vào các tuần sau (bài thứ 3 là quiz). 18 bài: 17 bài giao đến
# tuần 5, 1 bài (Đồ thị, tuần 6) chưa giao.
SCHEDULE_WEEKS: dict[int, tuple[int, int, int]] = {
    1: (1, 2, 3),
    2: (1, 2, 4),
    3: (2, 3, 4),
    4: (3, 4, 5),
    5: (4, 5, 6),
    6: (1, 3, 5),
}
# (tổng số câu, điểm tối đa): thang điểm khác nhau để kiểm tra việc quy đổi ra phần trăm.
EXERCISE_SHAPE = (10, 10.0)
QUIZ_SHAPE = (20, 20.0)


@dataclass(frozen=True)
class AssessmentSpec:
    key: str  # "T4-2" = chủ đề 4, bài thứ 2
    topic_no: int
    n: int  # 1..3
    week: int
    type: str
    title: str
    total_questions: int
    max_score: float


def build_schedule() -> list[AssessmentSpec]:
    specs = []
    for topic_no, weeks in SCHEDULE_WEEKS.items():
        topic_name = TOPICS[topic_no - 1][0]
        for n, week in enumerate(weeks, start=1):
            is_quiz = n == 3
            total, max_score = QUIZ_SHAPE if is_quiz else EXERCISE_SHAPE
            specs.append(
                AssessmentSpec(
                    key=f"T{topic_no}-{n}",
                    topic_no=topic_no,
                    n=n,
                    week=week,
                    type=(AssessmentType.QUIZ if is_quiz else AssessmentType.EXERCISE).value,
                    title=f"{topic_name} – " + ("Quiz" if is_quiz else f"Bài tập {n}"),
                    total_questions=total,
                    max_score=max_score,
                )
            )
    return sorted(specs, key=lambda s: (s.week, s.topic_no))


# ---------------------------------------------------------------------------------------
# Hồ sơ sinh viên mô phỏng
# ---------------------------------------------------------------------------------------
@dataclass(frozen=True)
class StudentProfile:
    username: str
    story: str
    # Điểm % cơ sở theo chủ đề (1..6); điểm thật = cơ sở + slope * (tuần - 3) + nhiễu ±noise.
    topic_base: dict[int, float]
    slope: float = 0.0
    noise: float = 4.0
    first_week: int = 1  # tuần bắt đầu làm bài (bài giao trước đó bỏ lỡ)
    skip: frozenset[str] = frozenset()  # bài không làm
    # Ghi đè điểm % chính xác của lần làm đầu (dùng để chạm ngưỡng 75% / 50%).
    overrides: dict[str, float] = field(default_factory=dict)
    # Làm lại bài: key -> điểm % của lần làm thứ 2 (lần này mới được tính).
    retries: dict[str, float] = field(default_factory=dict)
    study_minutes_per_week: int = 240


PROFILES: list[StudentProfile] = [
    StudentProfile(
        username="sv01",
        story="Đang tiến bộ rõ (xu hướng tăng); làm đủ mọi bài; làm lại 1 bài để cải thiện.",
        topic_base={1: 78, 2: 76, 3: 68, 4: 68, 5: 58, 6: 80},
        slope=9.0,
        overrides={"T3-1": 50.0},  # lần 1 chỉ 50%, làm lại được 70%
        retries={"T3-1": 70.0},
        study_minutes_per_week=300,
    ),
    StudentProfile(
        username="sv02",
        story="Yếu ở Cây nhị phân và Đồ thị, kết quả đang đi xuống; bỏ lỡ 2 bài.",
        topic_base={1: 82, 2: 74, 3: 66, 4: 44, 5: 32, 6: 64},
        slope=-7.0,
        skip=frozenset({"T4-3", "T6-2"}),
        study_minutes_per_week=150,
    ),
    StudentProfile(
        username="sv03",
        story="Học tốt toàn diện, điểm cao và ổn định; không có chủ đề yếu.",
        topic_base={1: 90, 2: 88, 3: 86, 4: 82, 5: 80, 6: 92},
        slope=0.0,
        noise=3.0,
        study_minutes_per_week=330,
    ),
    StudentProfile(
        username="sv04",
        story="Bắt đầu muộn (từ tuần 3): thiếu dữ liệu, có chủ đề chưa làm bài nào.",
        topic_base={1: 70, 2: 62, 3: 58, 4: 66, 5: 55, 6: 72},
        first_week=3,
        skip=frozenset({"T2-3", "T6-2"}),
        study_minutes_per_week=90,
    ),
    StudentProfile(
        username="sv05",
        story="Trung bình, ổn định; có chủ đề đúng ngưỡng 75% và 50%; làm lại 1 bài.",
        topic_base={1: 66, 2: 70, 3: 56, 4: 64, 5: 60, 6: 68},
        slope=0.0,
        noise=2.0,
        overrides={
            "T2-1": 70.0,
            "T2-2": 80.0,
            "T2-3": 75.0,  # TB chủ đề 2 = (70 + 80 + 75) / 3 = 75.0 đúng ngưỡng "mạnh"
            "T3-2": 50.0,
            "T3-3": 50.0,
            "T3-1": 50.0,  # TB chủ đề 3 = 50.0 đúng ngưỡng "trung bình"
            "T6-1": 40.0,  # lần 1 chỉ 40%, làm lại được 60% (xem retries)
        },
        retries={"T6-1": 60.0},
        study_minutes_per_week=210,
    ),
]


# ---------------------------------------------------------------------------------------
# Lỗi, kết quả trả về
# ---------------------------------------------------------------------------------------
class SeedError(Exception):
    """Lỗi người dùng có thể tự xử lý (hiển thị gọn, không in traceback)."""


@dataclass
class SeedSummary:
    course_code: str
    start_date: str
    current_week: int
    password: str
    counts: dict[str, int]
    students: list[tuple[str, str, str]]  # (username, display_name, câu chuyện)


# ---------------------------------------------------------------------------------------
# Tiện ích
# ---------------------------------------------------------------------------------------
def _rng(*parts: object) -> random.Random:
    """Bộ sinh số ngẫu nhiên xác định, độc lập theo từng khóa (không phụ thuộc thứ tự gọi)."""
    return random.Random("|".join(str(p) for p in parts))


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _local_dt(day: date, hour: int, minute: int) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=VN_TZ)


def _correct_count(pct: float, total: int) -> int:
    return max(0, min(total, int(pct / 100 * total + 0.5)))


# ---------------------------------------------------------------------------------------
# Sinh dữ liệu
# ---------------------------------------------------------------------------------------
def _completion_time(
    seed: int,
    username: str,
    key: str,
    attempt: int,
    week_start: date,
    now: datetime,
    floor: datetime | None,
) -> datetime:
    """Thời điểm hoàn thành: trong tuần của bài (lần 1) hoặc 1-3 ngày sau lần trước (làm lại)."""
    rng = _rng(seed, username, key, attempt, "time")
    if attempt == 1:
        today_local = now.astimezone(VN_TZ).date()
        max_offset = 6
        if week_start + timedelta(days=6) > today_local:  # tuần hiện tại: chưa tới Chủ nhật
            max_offset = (today_local - week_start).days
        day = week_start + timedelta(days=rng.randint(min(1, max_offset), max_offset))
        done = _local_dt(day, rng.randint(8, 22), rng.randint(0, 59))
    else:
        assert floor is not None
        done = floor + timedelta(days=rng.randint(1, 3), hours=rng.randint(0, 5))
    if done > now:  # không bao giờ sinh dữ liệu ở tương lai
        done = now - timedelta(minutes=rng.randint(5, 180))
    return done


def _make_results(
    profile: StudentProfile,
    user: User,
    assessments: dict[str, Assessment],
    specs: dict[str, AssessmentSpec],
    week_starts: dict[int, date],
    now: datetime,
    seed: int,
) -> list[Result]:
    rows: list[Result] = []
    for spec in sorted(specs.values(), key=lambda s: (s.week, s.topic_no)):
        if spec.week > CURRENT_WEEK or spec.week < profile.first_week or spec.key in profile.skip:
            continue
        rng = _rng(seed, profile.username, spec.key, "score")
        if spec.key in profile.overrides:
            pct = profile.overrides[spec.key]
        else:
            pct = (
                profile.topic_base[spec.topic_no]
                + profile.slope * (spec.week - 3)
                + rng.uniform(-profile.noise, profile.noise)
            )
        attempts = [(1, pct)]
        if spec.key in profile.retries:
            attempts.append((2, profile.retries[spec.key]))

        done_at: datetime | None = None
        for attempt, attempt_pct in attempts:
            correct = _correct_count(attempt_pct, spec.total_questions)
            done_at = _completion_time(
                seed, profile.username, spec.key, attempt, week_starts[spec.week], now, done_at
            )
            r = _rng(seed, profile.username, spec.key, attempt, "duration")
            lo, hi = (900, 2400) if spec.type == AssessmentType.QUIZ.value else (600, 1800)
            duration = r.randint(lo, hi)
            rows.append(
                Result(
                    user_id=user.id,
                    assessment_id=assessments[spec.key].id,
                    attempt_no=attempt,
                    score=correct * spec.max_score / spec.total_questions,
                    wrong_count=spec.total_questions - correct,
                    started_at=to_iso(done_at - timedelta(seconds=duration)),
                    completed_at=to_iso(done_at),
                    duration_seconds=duration,
                )
            )
    return rows


def _make_sessions(
    profile: StudentProfile,
    user: User,
    course: Course,
    topics: list[Topic],
    specs: dict[str, AssessmentSpec],
    week_starts: dict[int, date],
    now: datetime,
    seed: int,
) -> list[StudySession]:
    rows: list[StudySession] = []
    today_local = now.astimezone(VN_TZ).date()
    for week in range(profile.first_week, CURRENT_WEEK + 1):
        rng = _rng(seed, profile.username, "sessions", week)
        # Chủ đề đang học: có bài trong tuần này hoặc tuần trước.
        active = sorted({s.topic_no for s in specs.values() if s.week in (week, week - 1)})
        n_sessions = rng.randint(2, 4)
        per_session = profile.study_minutes_per_week / n_sessions
        for _ in range(n_sessions):
            day = week_starts[week] + timedelta(days=rng.randint(0, 6))
            started = _local_dt(day, rng.randint(7, 21), rng.choice((0, 15, 30, 45)))
            minutes = max(15, round(per_session * rng.uniform(0.7, 1.3)))
            topic_no = rng.choice(active) if active and rng.random() > 0.2 else None
            if day > today_local or started + timedelta(minutes=minutes) > now:
                continue  # chưa xảy ra
            rows.append(
                StudySession(
                    user_id=user.id,
                    course_id=course.id,
                    topic_id=topics[topic_no - 1].id if topic_no else None,
                    started_at=to_iso(started),
                    duration_seconds=minutes * 60,
                    source=SessionSource.SEED.value,
                )
            )
    return rows


def reset_demo_data(session: Session) -> None:
    """Xóa dữ liệu mô phỏng cũ. Không đụng tới tài khoản thật (is_synthetic = 0)."""
    session.execute(delete(Course).where(Course.code == DEMO_COURSE_CODE))
    session.execute(delete(User).where(User.is_synthetic.is_(True)))
    session.flush()


def seed_demo_data(
    session: Session,
    *,
    now: datetime,
    rng_seed: int = DEFAULT_RNG_SEED,
    password: str = DEFAULT_PASSWORD,
    reset: bool = False,
) -> SeedSummary:
    """Tạo dữ liệu mô phỏng. Không commit: người gọi quyết định commit hay rollback."""
    if now.tzinfo is None:
        raise ValueError("`now` phải có múi giờ")

    if not inspect(session.get_bind()).has_table("users"):
        raise SeedError("Chưa có bảng trong cơ sở dữ liệu. Hãy chạy trước: alembic upgrade head")

    exists = session.scalar(select(Course.id).where(Course.code == DEMO_COURSE_CODE))
    if exists and not reset:
        raise SeedError(
            f"Đã có dữ liệu mô phỏng (môn {DEMO_COURSE_CODE}). Dùng --reset để xóa và tạo lại."
        )
    usernames = [p.username for p in PROFILES]
    taken = session.scalars(
        select(User.username).where(User.username.in_(usernames), User.is_synthetic.is_(False))
    ).all()
    if taken:
        raise SeedError(f"Tên đăng nhập {', '.join(taken)} đã thuộc về tài khoản thật.")
    if reset:
        reset_demo_data(session)

    today_local = now.astimezone(VN_TZ).date()
    start = _monday(today_local) - timedelta(weeks=CURRENT_WEEK - 1)
    week_starts = {w: start + timedelta(weeks=w - 1) for w in range(1, TOTAL_WEEKS + 1)}

    course = Course(
        code=DEMO_COURSE_CODE,
        name=COURSE_NAME,
        description=COURSE_DESCRIPTION,
        start_date=start.isoformat(),
        total_weeks=TOTAL_WEEKS,
    )
    course.topics = [
        Topic(name=name, description=desc, order_no=i) for i, (name, desc) in enumerate(TOPICS, 1)
    ]
    session.add(course)
    session.flush()

    specs = {s.key: s for s in build_schedule()}
    assessments: dict[str, Assessment] = {}
    for spec in specs.values():
        assessments[spec.key] = Assessment(
            topic_id=course.topics[spec.topic_no - 1].id,
            title=spec.title,
            type=spec.type,
            week_no=spec.week,
            total_questions=spec.total_questions,
            max_score=spec.max_score,
            due_date=(week_starts[spec.week] + timedelta(days=6)).isoformat(),
        )
    session.add_all(assessments.values())
    session.flush()

    n_results = n_sessions = 0
    students = []
    for i, profile in enumerate(PROFILES, start=1):
        user = User(
            username=profile.username,
            password_hash=hash_password(password),
            display_name=f"Sinh viên {i:02d} (mô phỏng)",
            role=Role.STUDENT.value,
            is_synthetic=True,
        )
        session.add(user)
        session.flush()
        results = _make_results(profile, user, assessments, specs, week_starts, now, rng_seed)
        sessions = _make_sessions(
            profile, user, course, course.topics, specs, week_starts, now, rng_seed
        )
        session.add_all(results + sessions)
        n_results += len(results)
        n_sessions += len(sessions)
        students.append((user.username, user.display_name, profile.story))
    session.flush()

    return SeedSummary(
        course_code=course.code,
        start_date=course.start_date,
        current_week=CURRENT_WEEK,
        password=password,
        counts={
            "courses": 1,
            "topics": len(TOPICS),
            "assessments": len(assessments),
            "users": len(PROFILES),
            "results": n_results,
            "study_sessions": n_sessions,
        },
        students=students,
    )


# ---------------------------------------------------------------------------------------
# Dòng lệnh
# ---------------------------------------------------------------------------------------
def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m app.seed.seed_data",
        description="Sinh dữ liệu mô phỏng cho StudyLens (1 môn, 6 chủ đề, 5 sinh viên giả).",
    )
    p.add_argument("--reset", action="store_true", help="xóa dữ liệu mô phỏng cũ rồi tạo lại")
    p.add_argument(
        "--today",
        type=date.fromisoformat,
        metavar="YYYY-MM-DD",
        help="coi hôm nay là ngày này (mặc định: ngày thật)",
    )
    p.add_argument("--seed", type=int, default=DEFAULT_RNG_SEED, help="hạt giống số ngẫu nhiên")
    p.add_argument("--password", default=DEFAULT_PASSWORD, help="mật khẩu chung của tài khoản demo")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    # Terminal Windows (Git Bash) thường không dùng UTF-8: tránh lỗi UnicodeEncodeError
    # khi in tiếng Việt.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    args = _parse_args(argv)
    if args.today:
        now = datetime.combine(args.today, time(18, 0), tzinfo=VN_TZ)
    else:
        now = datetime.now(UTC)

    with SessionLocal() as session:
        try:
            summary = seed_demo_data(
                session, now=now, rng_seed=args.seed, password=args.password, reset=args.reset
            )
            session.commit()
        except SeedError as e:
            session.rollback()
            print(f"Lỗi: {e}", file=sys.stderr)
            return 1

    c = summary.counts
    print("Đã tạo dữ liệu mô phỏng (KHÔNG phải dữ liệu thật).")
    print(
        f"  Môn {summary.course_code}: bắt đầu {summary.start_date}, "
        f"hiện đang tuần {summary.current_week}/{TOTAL_WEEKS}"
    )
    print(
        f"  {c['topics']} chủ đề, {c['assessments']} bài, {c['users']} sinh viên, "
        f"{c['results']} lần làm bài, {c['study_sessions']} phiên học"
    )
    print(f"\nTài khoản đăng nhập thử (mật khẩu chung: {summary.password})")
    for username, display_name, story in summary.students:
        print(f"  {username:<6} {display_name:<26} {story}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
