"""Bản tính chỉ số THAM CHIẾU, viết thẳng theo docs/03-api/metrics-definition.md (dùng trong test).

Cố ý viết đơn giản và tách biệt hoàn toàn với `app/analytics/` sẽ làm sau, để dùng làm giá trị
đối chiếu cho NFR03 (độ chính xác của chỉ số). Mọi so sánh với ngưỡng đều dùng giá trị ĐÃ LÀM TRÒN
(1 chữ số thập phân, half-up) bằng Decimal, để số hiển thị và nhãn luôn khớp nhau.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Assessment, Course, Result, Topic

# ---- Tham số (khớp bảng "Tham số" trong metrics-definition.md) ----
STRONG_MIN = Decimal("75")
MEDIUM_MIN = Decimal("50")
MIN_ASSESSMENTS_FOR_LABEL = 2
TREND_THRESHOLD = 5.0  # xu hướng theo TUẦN (cả môn), điểm %; giữ dạng float cho test cũ
# Xu hướng theo CHỦ ĐỀ (bài gần nhất so với bài liền trước) dùng ngưỡng riêng, lớn hơn, vì mỗi bài
# chỉ có 10 hoặc 20 câu nên điểm nhảy theo bậc 10% hoặc 5% và ngưỡng 5 sẽ bắt nhầm nhiễu.
TOPIC_TREND_THRESHOLD = Decimal("10")
WRONG_RATE_TRIGGER = Decimal("40")  # % câu sai từ mức này trở lên -> many_wrong_answers
W_LOW_AVERAGE, W_WRONG, W_DECLINE = Decimal("0.5"), Decimal("0.3"), Decimal("0.2")
DECLINE_CAP = Decimal("30")  # điểm % giảm tối đa được tính vào điểm ưu tiên
MAX_RECOMMENDATIONS = 5

_TENTH = Decimal("0.1")


def r1(x) -> Decimal:
    """Làm tròn half-up 1 chữ số thập phân. Loại nhiễu số thực (round 9) trước khi làm tròn."""
    d = x if isinstance(x, Decimal) else Decimal(str(round(float(x), 9)))
    return d.quantize(_TENTH, rounding=ROUND_HALF_UP)


def fmt(d: Decimal) -> str:
    """Định dạng số theo kiểu Việt Nam, bỏ ',0' thừa: 45,0 -> '45'; 78,3 -> '78,3'."""
    s = f"{d:.1f}".replace(".", ",")
    return s[:-2] if s.endswith(",0") else s


@dataclass
class TopicStat:
    name: str
    avg_pct: float | None
    done: int
    wrong_total: int
    label: str  # strong | medium | weak | insufficient | no_data
    assigned: int = 0
    total_questions: int = 0
    wrong_rate_pct: float | None = None
    trend: str = "insufficient"  # up | down | stable | insufficient
    trend_delta: float | None = None
    latest_title: str | None = None
    latest_pct: float | None = None
    previous_pct: float | None = None


@dataclass
class StudentMetrics:
    topics: dict[int, TopicStat]  # order_no -> thống kê
    completion: tuple[int, int]  # (đã làm, đã giao)
    weekly_avg: dict[int, float]
    trend: str
    trend_delta: float | None
    overall_avg_pct: float | None = None


@dataclass
class Recommendation:
    rank: int
    topic_no: int
    topic_name: str
    priority_score: float
    reasons: list[tuple[str, str]]  # (code, câu giải thích)
    reason_text: str
    metrics: dict = field(default_factory=dict)


def current_week(course: Course, today: date) -> int:
    """Tuần hiện tại: 0 = chưa bắt đầu; không vượt quá tổng số tuần của môn."""
    days = (today - date.fromisoformat(course.start_date)).days
    return 0 if days < 0 else min(days // 7 + 1, course.total_weeks)


def latest_attempts(session: Session, user_id: int) -> list[tuple[Result, Assessment]]:
    rows = session.execute(
        select(Result, Assessment)
        .join(Assessment, Assessment.id == Result.assessment_id)
        .where(Result.user_id == user_id)
    ).all()
    best: dict[int, tuple[Result, Assessment]] = {}
    for result, assessment in rows:
        cur = best.get(assessment.id)
        if cur is None or result.attempt_no > cur[0].attempt_no:
            best[assessment.id] = (result, assessment)
    return list(best.values())


def pct(result: Result, assessment: Assessment) -> float:
    return result.score / assessment.max_score * 100


def label_for(avg: float | None, done: int) -> str:
    if done == 0 or avg is None:
        return "no_data"
    if done < MIN_ASSESSMENTS_FOR_LABEL:
        return "insufficient"
    rounded = r1(avg)
    if rounded >= STRONG_MIN:
        return "strong"
    if rounded >= MEDIUM_MIN:
        return "medium"
    return "weak"


def trend_for(delta: Decimal | None, threshold: Decimal | None = None) -> str:
    if delta is None:
        return "insufficient"
    threshold = Decimal(str(TREND_THRESHOLD)) if threshold is None else threshold
    if delta >= threshold:
        return "up"
    if delta <= -threshold:
        return "down"
    return "stable"


def compute(session: Session, user_id: int, course: Course, today: date) -> StudentMetrics:
    attempts = latest_attempts(session, user_id)
    topics = session.scalars(
        select(Topic).where(Topic.course_id == course.id).order_by(Topic.order_no)
    ).all()
    week_now = current_week(course, today)

    stats: dict[int, TopicStat] = {}
    for topic in topics:
        mine = sorted(
            ((r, a) for r, a in attempts if a.topic_id == topic.id),
            key=lambda ra: (ra[1].week_no, ra[1].id),
        )
        avg = sum(pct(r, a) for r, a in mine) / len(mine) if mine else None
        total_q = sum(a.total_questions for _, a in mine)
        wrong = sum(r.wrong_count for r, _ in mine)
        n_assigned = len(
            session.scalars(
                select(Assessment.id).where(
                    Assessment.topic_id == topic.id, Assessment.week_no <= week_now
                )
            ).all()
        )
        stat = TopicStat(
            name=topic.name,
            avg_pct=None if avg is None else float(r1(avg)),
            done=len(mine),
            wrong_total=wrong,
            label=label_for(avg, len(mine)),
            assigned=n_assigned,
            total_questions=total_q,
            wrong_rate_pct=float(r1(Decimal(wrong) / Decimal(total_q) * 100)) if total_q else None,
        )
        if len(mine) >= 2:  # xu hướng theo chủ đề: bài gần nhất so với bài liền trước
            (r_last, a_last), (r_prev, a_prev) = mine[-1], mine[-2]
            delta = r1(pct(r_last, a_last)) - r1(pct(r_prev, a_prev))
            stat.trend = trend_for(delta, TOPIC_TREND_THRESHOLD)
            stat.trend_delta = float(delta)
            stat.latest_title = a_last.title
            stat.latest_pct = float(r1(pct(r_last, a_last)))
            stat.previous_pct = float(r1(pct(r_prev, a_prev)))
        stats[topic.order_no] = stat

    assigned_ids = set(
        session.scalars(
            select(Assessment.id)
            .join(Topic, Topic.id == Assessment.topic_id)
            .where(Topic.course_id == course.id, Assessment.week_no <= week_now)
        ).all()
    )
    done_ids = {a.id for _, a in attempts}
    completion = (len(done_ids & assigned_ids), len(assigned_ids))

    by_week: dict[int, list[float]] = {}
    for r, a in attempts:
        by_week.setdefault(a.week_no, []).append(pct(r, a))
    weekly = {w: r1(sum(v) / len(v)) for w, v in by_week.items()}
    weeks = sorted(weekly)
    delta = weekly[weeks[-1]] - weekly[weeks[-2]] if len(weeks) >= 2 else None
    overall = r1(sum(pct(r, a) for r, a in attempts) / len(attempts)) if attempts else None
    return StudentMetrics(
        topics=stats,
        completion=completion,
        weekly_avg={w: float(v) for w, v in weekly.items()},
        trend=trend_for(delta),
        trend_delta=None if delta is None else float(delta),
        overall_avg_pct=None if overall is None else float(overall),
    )


def recommend(m: StudentMetrics) -> list[Recommendation]:
    """Gợi ý ôn tập theo metrics-definition.md mục 6. Chỉ sinh gợi ý loại `review_topic`."""
    candidates = []
    for topic_no, t in m.topics.items():
        if t.label in ("insufficient", "no_data"):
            continue  # chưa đủ bằng chứng để gợi ý
        avg = Decimal(str(t.avg_pct))
        wrong_rate = Decimal(str(t.wrong_rate_pct))
        reasons: list[tuple[str, str]] = []
        if t.label == "weak":
            reasons.append(
                (
                    "low_average",
                    f"Điểm trung bình của chủ đề là {fmt(avg)}%, thuộc mức yếu (dưới 50%).",
                )
            )
        if wrong_rate >= WRONG_RATE_TRIGGER:
            reasons.append(
                (
                    "many_wrong_answers",
                    f"Bạn trả lời sai {t.wrong_total}/{t.total_questions} câu "
                    f"({fmt(wrong_rate)}%) ở các bài đã làm.",
                )
            )
        decline = Decimal(0)
        if t.trend == "down" and t.label != "strong":  # chủ đề mạnh không cần ôn
            delta = Decimal(str(t.trend_delta))
            decline = min(-delta, DECLINE_CAP) / DECLINE_CAP * 100
            reasons.append(
                (
                    "declining_trend",
                    f"Bài gần nhất ({t.latest_title}) đạt {fmt(Decimal(str(t.latest_pct)))}%, "
                    f"giảm {fmt(-delta)} điểm % so với bài trước ({fmt(Decimal(str(t.previous_pct)))}%).",
                )
            )
        if not reasons:
            continue
        priority = r1(W_LOW_AVERAGE * (100 - avg) + W_WRONG * wrong_rate + W_DECLINE * decline)
        candidates.append((priority, avg, topic_no, t, reasons))

    candidates.sort(key=lambda c: (-c[0], c[1], c[2]))
    out = []
    for rank, (priority, _avg, topic_no, t, reasons) in enumerate(
        candidates[:MAX_RECOMMENDATIONS], start=1
    ):
        out.append(
            Recommendation(
                rank=rank,
                topic_no=topic_no,
                topic_name=t.name,
                priority_score=float(priority),
                reasons=reasons,
                reason_text=" ".join(text for _, text in reasons),
                metrics={
                    "avg_pct": t.avg_pct,
                    "done": t.done,
                    "wrong_total": t.wrong_total,
                    "total_questions": t.total_questions,
                    "wrong_rate_pct": t.wrong_rate_pct,
                    "trend": {
                        "status": t.trend,
                        "delta_pct": t.trend_delta,
                        "latest_pct": t.latest_pct,
                        "previous_pct": t.previous_pct,
                    },
                },
            )
        )
    return out
