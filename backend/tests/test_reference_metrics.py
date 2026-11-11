"""Kiểm tra bản tính tham chiếu: các ca biên của quy tắc, rồi kết quả trên dữ liệu mô phỏng."""

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models import Course, User
from app.seed.seed_data import DEMO_COURSE_CODE, VN_TZ, seed_demo_data
from tests import reference_metrics as ref

D = Decimal


# ------------------------------------------------------------------ làm tròn
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (74.99999999999999, "75.0"),  # nhiễu số thực không được làm rơi nhãn
        (74.95, "75.0"),  # half-up, không phải làm tròn chẵn của Python
        (74.94, "74.9"),
        (49.95, "50.0"),
        (0.05, "0.1"),
        (100, "100.0"),
    ],
)
def test_r1_is_half_up_and_ignores_float_noise(raw, expected):
    assert ref.r1(raw) == D(expected)


@pytest.mark.parametrize(
    ("value", "text"),
    [(D("45.0"), "45"), (D("78.3"), "78,3"), (D("100.0"), "100"), (D("0.0"), "0")],
)
def test_fmt_uses_vietnamese_decimal_comma_without_trailing_zero(value, text):
    assert ref.fmt(value) == text


# ------------------------------------------------------------------ nhãn và xu hướng
@pytest.mark.parametrize(
    ("avg", "done", "label"),
    [
        (75.0, 2, "strong"),  # đúng ngưỡng: "từ 75% trở lên"
        (74.96, 2, "strong"),  # hiển thị 75,0 nên nhãn phải là mạnh
        (74.94, 2, "medium"),
        (50.0, 2, "medium"),  # đúng ngưỡng: "từ 50% đến dưới 75%"
        (49.95, 2, "medium"),  # hiển thị 50,0
        (49.94, 2, "weak"),
        (0.0, 2, "weak"),  # điểm 0 là dữ liệu thật, không phải "chưa có dữ liệu"
        (95.0, 1, "insufficient"),  # < 2 bài
        (None, 0, "no_data"),
    ],
)
def test_label_boundaries(avg, done, label):
    assert ref.label_for(avg, done) == label


@pytest.mark.parametrize(
    ("delta", "threshold", "status"),
    [
        (D("5.0"), None, "up"),
        (D("4.9"), None, "stable"),
        (D("-4.9"), None, "stable"),
        (D("-5.0"), None, "down"),
        (None, None, "insufficient"),
        (D("9.9"), ref.TOPIC_TREND_THRESHOLD, "stable"),
        (D("-10.0"), ref.TOPIC_TREND_THRESHOLD, "down"),
    ],
)
def test_trend_boundaries(delta, threshold, status):
    assert ref.trend_for(delta, threshold) == status


@pytest.mark.parametrize(
    ("today", "week"),
    [
        (date(2026, 10, 11), 0),  # chủ nhật trước ngày bắt đầu: chưa bắt đầu
        (date(2026, 10, 12), 1),
        (date(2026, 10, 18), 1),
        (date(2026, 10, 19), 2),
        (date(2026, 11, 22), 6),
        (date(2027, 3, 1), 6),  # sau khi môn kết thúc: không vượt tổng số tuần
    ],
)
def test_current_week_is_clamped(today, week):
    course = SimpleNamespace(start_date="2026-10-12", total_weeks=6)
    assert ref.current_week(course, today) == week


# ------------------------------------------------------------------ gợi ý
def _topic(**kw):
    base = {
        "name": "Chủ đề", "avg_pct": 60.0, "done": 3, "wrong_total": 10, "label": "medium",
        "assigned": 3, "total_questions": 40, "wrong_rate_pct": 25.0,
        "trend": "stable", "trend_delta": 0.0, "latest_title": "Bài", "latest_pct": 60.0,
        "previous_pct": 60.0,
    }  # fmt: skip
    return ref.TopicStat(**{**base, **kw})


def _metrics(*topics):
    return ref.StudentMetrics(
        topics={i: t for i, t in enumerate(topics, 1)},
        completion=(0, 0), weekly_avg={}, trend="stable", trend_delta=0.0,
    )  # fmt: skip


@pytest.mark.parametrize(("rate", "recommended"), [(40.0, True), (39.9, False)])
def test_wrong_rate_threshold_is_inclusive(rate, recommended):
    recs = ref.recommend(_metrics(_topic(wrong_rate_pct=rate)))
    assert bool(recs) is recommended
    if recommended:
        assert [c for c, _ in recs[0].reasons] == ["many_wrong_answers"]


def test_strong_topic_is_never_recommended_even_if_declining():
    t = _topic(label="strong", avg_pct=85.0, trend="down", trend_delta=-15.0, wrong_rate_pct=45.0)
    # chủ đề mạnh vẫn có thể bị cảnh báo sai nhiều, nhưng KHÔNG vì xu hướng giảm
    recs = ref.recommend(_metrics(t))
    assert [c for c, _ in recs[0].reasons] == ["many_wrong_answers"]
    t = _topic(label="strong", avg_pct=85.0, trend="down", trend_delta=-15.0, wrong_rate_pct=15.0)
    assert ref.recommend(_metrics(t)) == []


def test_topics_without_enough_data_are_not_recommended():
    weak_but_thin = _topic(label="insufficient", avg_pct=20.0, done=1, wrong_rate_pct=80.0)
    assert (
        ref.recommend(_metrics(weak_but_thin, _topic(label="no_data", avg_pct=None, done=0))) == []
    )


def test_priority_formula_matches_the_worked_example():
    # avg 25 -> 0.5*75 = 37.5 ; sai 75% -> 0.3*75 = 22.5 ; giảm 10 -> 0.2*(10/30*100) = 6.666...
    t = _topic(label="weak", avg_pct=25.0, wrong_rate_pct=75.0, trend="down", trend_delta=-10.0)
    assert ref.recommend(_metrics(t))[0].priority_score == 66.7


def test_decline_component_is_capped_at_30_points():
    big = _topic(label="weak", avg_pct=40.0, wrong_rate_pct=50.0, trend="down", trend_delta=-60.0)
    cap = _topic(label="weak", avg_pct=40.0, wrong_rate_pct=50.0, trend="down", trend_delta=-30.0)
    assert (
        ref.recommend(_metrics(big))[0].priority_score
        == ref.recommend(_metrics(cap))[0].priority_score
    )


def test_ties_break_by_lower_average_then_topic_order_and_list_is_capped():
    same = {"label": "weak", "avg_pct": 30.0, "wrong_rate_pct": 70.0}
    topics = [_topic(name=f"T{i}", **same) for i in range(1, 8)]
    recs = ref.recommend(_metrics(*topics))
    assert len(recs) == ref.MAX_RECOMMENDATIONS == 5
    assert [r.topic_no for r in recs] == [1, 2, 3, 4, 5]
    assert [r.rank for r in recs] == [1, 2, 3, 4, 5]
    lower_avg = _topic(name="thấp hơn", label="weak", avg_pct=20.0, wrong_rate_pct=70.0)
    assert ref.recommend(_metrics(*topics, lower_avg))[0].topic_name == "thấp hơn"


# ------------------------------------------------------------------ dữ liệu mô phỏng
NOW = datetime(2026, 11, 12, 18, 0, tzinfo=VN_TZ)


@pytest.fixture
def recs_by_student(session):
    seed_demo_data(session, now=NOW)
    session.commit()
    course = session.scalar(select(Course).where(Course.code == DEMO_COURSE_CODE))
    out = {}
    for user in session.scalars(select(User)):
        m = ref.compute(session, user.id, course, NOW.date())
        out[user.username] = ref.recommend(m)
    return out


def _summary(recs):
    return [(r.topic_name, r.priority_score, [c for c, _ in r.reasons]) for r in recs]


def test_seeded_students_get_the_intended_recommendations(recs_by_student):
    r = recs_by_student
    assert r["sv01"] == [] and r["sv03"] == []  # đang tiến bộ / mọi chủ đề đều mạnh
    assert _summary(r["sv02"]) == [
        ("Đồ thị", 66.7, ["low_average", "many_wrong_answers", "declining_trend"]),
        ("Cây nhị phân", 50.7, ["low_average", "many_wrong_answers", "declining_trend"]),
        ("Sắp xếp và tìm kiếm", 49.5, ["many_wrong_answers", "declining_trend"]),
    ]
    assert _summary(r["sv04"]) == [
        ("Đồ thị", 42.7, ["many_wrong_answers", "declining_trend"]),
        ("Ngăn xếp và hàng đợi", 34.2, ["many_wrong_answers"]),
    ]
    # sv05: tỷ lệ sai của Đồ thị đúng 40,0% (ca biên của many_wrong_answers)
    assert _summary(r["sv05"]) == [
        ("Ngăn xếp và hàng đợi", 40.0, ["many_wrong_answers"]),
        ("Đồ thị", 32.0, ["many_wrong_answers"]),
    ]


def test_reason_text_is_built_only_from_numbers_in_the_data(recs_by_student):
    top = recs_by_student["sv02"][0]
    assert top.reason_text == (
        "Điểm trung bình của chủ đề là 25%, thuộc mức yếu (dưới 50%). "
        "Bạn trả lời sai 15/20 câu (75%) ở các bài đã làm. "
        "Bài gần nhất (Đồ thị – Bài tập 2) đạt 20%, giảm 10 điểm % so với bài trước (30%)."
    )
    assert top.metrics["wrong_total"] == 15 and top.metrics["total_questions"] == 20
