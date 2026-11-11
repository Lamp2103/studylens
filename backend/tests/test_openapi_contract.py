"""Kiểm tra hợp đồng API (docs/03-api/openapi.yaml) và các file JSON mẫu đi kèm.

Các test này bảo vệ ba điều: (1) spec hợp lệ OpenAPI 3.1, (2) mọi file mẫu khớp schema của nó,
(3) các file mẫu nhất quán với nhau và với quy tắc trong metrics-definition.md, vì frontend sẽ dùng
chúng làm dữ liệu giả (`src/mocks/`). Bỏ qua nếu repo không có thư mục docs/.
"""

import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate as validate_openapi

from app.main import app
from tests import reference_metrics as ref

API_DIR = Path(__file__).resolve().parents[2] / "docs" / "03-api"
SPEC_PATH = API_DIR / "openapi.yaml"

pytestmark = pytest.mark.skipif(
    not SPEC_PATH.exists(), reason="không thấy docs/03-api/openapi.yaml"
)

D = Decimal


@pytest.fixture(scope="module")
def spec():
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


def _example(name):
    return json.loads((API_DIR / "examples" / f"{name}.json").read_text(encoding="utf-8"))


def _schema_validator(spec, schema):
    # Gói schema cùng `components` để các $ref nội bộ ("#/components/schemas/...") tra được.
    return Draft202012Validator({**copy.deepcopy(schema), "components": spec["components"]})


def _media_examples(spec):
    """Mọi (schema, đường dẫn file mẫu) khai báo bằng externalValue trong spec."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            if "schema" in node and isinstance(node.get("examples"), dict):
                for ex in node["examples"].values():
                    if "externalValue" in ex:
                        found.append((node["schema"], ex["externalValue"]))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(spec)
    return found


# ------------------------------------------------------------------ spec
def test_spec_is_valid_openapi_31(spec):
    assert spec["openapi"].startswith("3.1")
    validate_openapi(spec)


def test_operations_follow_the_conventions(spec):
    ids, public = [], {"/health", "/auth/login"}
    for path, item in spec["paths"].items():
        for method, op in item.items():
            ids.append(op["operationId"])
            assert op["tags"] and op["summary"], f"{method} {path} thiếu tags/summary"
            if path not in public:
                assert "401" in op["responses"], f"{method} {path} cần khai báo 401"
            if path not in {"/health", "/auth/me"} and not path.startswith("/auth/"):
                assert op.get("x-requirements"), f"{method} {path} thiếu x-requirements"
    assert len(ids) == len(set(ids)), "operationId bị trùng"
    assert spec["security"] == [{"bearerAuth": []}]
    assert spec["paths"]["/health"]["get"]["security"] == []
    assert spec["paths"]["/auth/login"]["post"]["security"] == []


def test_every_mvp_requirement_is_covered_by_an_endpoint(spec):
    covered = {
        fr
        for item in spec["paths"].values()
        for op in item.values()
        for fr in op.get("x-requirements", [])
    }
    assert covered >= {"FR01", "FR02", "FR03", "FR04", "FR05", "FR06", "FR07", "FR08", "FR12"}
    assert covered.isdisjoint({"FR09", "FR10", "FR11"})  # các yêu cầu hoãn chưa có endpoint


# ------------------------------------------------------------------ file mẫu
def test_every_example_file_exists_validates_and_is_referenced(spec):
    refs = _media_examples(spec)
    assert refs
    for schema, rel in refs:
        path = API_DIR / rel
        assert path.exists(), f"thiếu file mẫu {rel}"
        errors = sorted(
            _schema_validator(spec, schema).iter_errors(
                json.loads(path.read_text(encoding="utf-8"))
            ),
            key=str,
        )
        assert not errors, f"{rel}: {errors[0].message} tại {list(errors[0].absolute_path)}"
    referenced = {Path(rel).name for _, rel in refs}
    on_disk = {p.name for p in (API_DIR / "examples").glob("*.json")}
    assert on_disk == referenced, f"file mẫu không được spec dùng: {on_disk - referenced}"


def test_validation_really_rejects_bad_data(spec):
    """Kiểm tra chính bộ kiểm tra: dữ liệu sai phải bị bắt."""
    schema = {"$ref": "#/components/schemas/DashboardSummary"}
    good = _example("dashboard-summary")
    assert not list(_schema_validator(spec, schema).iter_errors(good))

    missing = {k: v for k, v in good.items() if k != "trend"}
    bad_pct = {**good, "average_pct": 120}
    bad_label = {**good, "label_counts": {**good["label_counts"], "strong": "nhiều"}}
    bad_time = {**good, "as_of": "2026-11-12 11:00:00"}
    for bad in (missing, bad_pct, bad_label, bad_time):
        assert list(_schema_validator(spec, schema).iter_errors(bad))


# ------------------------------------------------------------------ nhất quán giữa các file mẫu
def test_topic_stats_follow_the_rules():
    topics = _example("topics")["items"]
    assert [t["order_no"] for t in topics] == sorted(t["order_no"] for t in topics)
    for t in topics:
        assert t["label"] == ref.label_for(t["avg_pct"], t["assessments_done"]), t["name"]
        assert (t["avg_pct"] is None) == (t["assessments_done"] == 0)
        assert t["assessments_done"] <= t["assessments_assigned"]
        if t["total_questions"]:
            rate = ref.r1(D(t["wrong_total"]) / D(t["total_questions"]) * 100)
            assert t["wrong_rate_pct"] == float(rate)
        else:
            assert t["wrong_rate_pct"] is None
        tr = t["trend"]
        if tr["status"] == "insufficient":
            assert tr["delta_pct"] is None
        else:
            delta = ref.r1(tr["latest_pct"]) - ref.r1(tr["previous_pct"])
            assert tr["delta_pct"] == float(delta)
            assert tr["status"] == ref.trend_for(delta, ref.TOPIC_TREND_THRESHOLD)


def test_dashboard_is_consistent_with_topics_and_rules():
    dash, topics = _example("dashboard-summary"), _example("topics")["items"]
    counts = {k: sum(t["label"] == k for t in topics) for k in dash["label_counts"]}
    assert dash["label_counts"] == counts and sum(counts.values()) == len(topics)

    rated = [t for t in topics if t["label"] in ("strong", "medium", "weak")]
    low = min(rated, key=lambda t: (t["avg_pct"], t["order_no"]))
    high = max(rated, key=lambda t: (t["avg_pct"], -t["order_no"]))
    assert dash["lowest_topic"] == {"id": low["id"], "name": low["name"], "avg_pct": low["avg_pct"]}
    assert dash["highest_topic"] == {
        "id": high["id"],
        "name": high["name"],
        "avg_pct": high["avg_pct"],
    }

    c = dash["completion"]
    assert c["pct"] == float(ref.r1(D(c["done"]) / D(c["assigned"]) * 100))
    assert c["assigned"] == sum(t["assessments_assigned"] for t in topics)
    assert c["done"] == sum(t["assessments_done"] for t in topics)
    assert dash["trend"] == _example("progress-weekly")["trend"]


def test_analysis_groups_match_topics_and_thresholds():
    analysis, topics = _example("analysis-strengths-weaknesses"), _example("topics")["items"]
    assert analysis["thresholds"] == {
        "strong_min_pct": int(ref.STRONG_MIN),
        "medium_min_pct": int(ref.MEDIUM_MIN),
        "min_assessments": ref.MIN_ASSESSMENTS_FOR_LABEL,
    }
    for label, group in analysis["groups"].items():
        assert {t["id"] for t in group} == {t["id"] for t in topics if t["label"] == label}
        assert all(t["label"] == label for t in group)
    weak = [t["avg_pct"] for t in analysis["groups"]["weak"]]
    assert weak == sorted(weak)  # yếu nhất trước
    strong = [t["avg_pct"] for t in analysis["groups"]["strong"]]
    assert strong == sorted(strong, reverse=True)


def test_recommendations_are_explainable_and_follow_the_formula():
    data, topics = _example("recommendations"), {t["id"]: t for t in _example("topics")["items"]}
    items = data["items"]
    assert data["empty_reason"] is None and 1 <= len(items) <= ref.MAX_RECOMMENDATIONS
    assert [r["rank"] for r in items] == list(range(1, len(items) + 1))
    assert [r["priority_score"] for r in items] == sorted(
        (r["priority_score"] for r in items), reverse=True
    )
    for r in items:
        t = topics[r["topic"]["id"]]
        codes = [x["code"] for x in r["reasons"]]
        assert r["reason_text"] == " ".join(x["detail"] for x in r["reasons"])
        # số liệu làm căn cứ phải đúng là số liệu của chủ đề
        m = r["metrics"]
        assert (m["avg_pct"], m["wrong_total"], m["total_questions"], m["done"]) == (
            t["avg_pct"], t["wrong_total"], t["total_questions"], t["assessments_done"],
        )  # fmt: skip
        assert m["trend"] == t["trend"] and m["wrong_rate_pct"] == t["wrong_rate_pct"]
        # lý do khớp điều kiện kích hoạt
        assert ("low_average" in codes) == (t["label"] == "weak")
        assert ("many_wrong_answers" in codes) == (
            D(str(t["wrong_rate_pct"])) >= ref.WRONG_RATE_TRIGGER
        )
        assert ("declining_trend" in codes) == (
            t["trend"]["status"] == "down" and t["label"] != "strong"
        )
        # điểm ưu tiên tính lại từ số liệu
        decline = D(0)
        if "declining_trend" in codes:
            decline = min(-D(str(t["trend"]["delta_pct"])), ref.DECLINE_CAP) / ref.DECLINE_CAP * 100
        expected = ref.r1(
            ref.W_LOW_AVERAGE * (100 - D(str(t["avg_pct"])))
            + ref.W_WRONG * D(str(t["wrong_rate_pct"]))
            + ref.W_DECLINE * decline
        )
        assert r["priority_score"] == float(expected), r["topic"]["name"]


def test_empty_recommendations_carry_a_reason():
    empty = _example("recommendations-empty")
    assert empty["items"] == [] and empty["empty_reason"] in {
        "no_topic_needs_review",
        "insufficient_data",
    }


def test_weekly_progress_is_complete_and_consistent():
    data, topics = _example("progress-weekly"), _example("topics")["items"]
    weeks = data["weeks"]
    assert [w["week_no"] for w in weeks] == list(range(1, data["total_weeks"] + 1))
    for w in weeks:
        expected = (
            "past" if w["week_no"] < data["current_week"]
            else "current" if w["week_no"] == data["current_week"] else "future"
        )  # fmt: skip
        assert w["state"] == expected
        assert w["assessments_done"] <= w["assessments_assigned"]
        assert (w["avg_pct"] is None) == (w["assessments_done"] == 0)
        assert sum(t["done"] for t in w["by_topic"]) == w["assessments_done"]
        if w["state"] == "future":
            assert w["assessments_assigned"] == 0 and w["by_topic"] == []
    assert sum(w["assessments_done"] for w in weeks) == sum(t["assessments_done"] for t in topics)
    with_data = [w for w in weeks if w["avg_pct"] is not None]
    delta = ref.r1(with_data[-1]["avg_pct"]) - ref.r1(with_data[-2]["avg_pct"])
    trend = data["trend"]
    assert (trend["latest_week"], trend["previous_week"]) == (
        with_data[-1]["week_no"],
        with_data[-2]["week_no"],
    )
    assert trend["delta_pct"] == float(delta) and trend["status"] == ref.trend_for(delta)


def test_topic_results_are_consistent_with_the_topic_list():
    detail, topics = _example("topic-results"), {t["id"]: t for t in _example("topics")["items"]}
    assert detail["topic"] == topics[detail["topic"]["id"]]
    assessments = detail["assessments"]
    assert [(a["week_no"], a["assessment_id"]) for a in assessments] == sorted(
        (a["week_no"], a["assessment_id"]) for a in assessments
    )
    for a in assessments:
        done = bool(a["attempts"])
        expected = (
            "done"
            if done
            else "not_done"
            if a["week_no"] <= detail["current_week"]
            else "not_assigned"
        )
        assert a["status"] == expected
        assert a["latest"] == (a["attempts"][-1] if done else None)
        assert [x["attempt_no"] for x in a["attempts"]] == list(range(1, len(a["attempts"]) + 1))
        for x in a["attempts"]:
            assert x["pct"] == float(ref.r1(D(str(x["score"])) / D(str(a["max_score"])) * 100))
            assert x["wrong_count"] <= a["total_questions"] and x["score"] <= a["max_score"]
    assert detail["topic"]["assessments_done"] == sum(a["status"] == "done" for a in assessments)


def test_result_create_example_is_consistent():
    req, res = _example("results-create-request"), _example("results-create-response")["result"]
    assert res["assessment_id"] == req["assessment_id"]
    assert (res["score"], res["wrong_count"], res["completed_at"]) == (
        req["score"], req["wrong_count"], req["completed_at"],
    )  # fmt: skip
    assert res["pct"] == float(ref.r1(D(str(res["score"])) / D(str(res["max_score"])) * 100))
    assert req["started_at"] <= req["completed_at"]


def test_login_and_me_describe_the_same_user():
    assert _example("auth-login")["user"] == _example("auth-me")
    assert (
        _example("auth-login")["user"]["is_synthetic"] is True
    )  # dữ liệu mô phỏng phải được đánh dấu


# ------------------------------------------------------------------ không lệch với mã đã cài đặt
def test_implemented_routes_match_the_contract(spec):
    """Mọi route đã cài đặt phải có trong spec (cùng phương thức, mã trả về và trường dữ liệu)."""
    implemented = app.openapi()
    checked = 0
    for path, methods in implemented["paths"].items():
        assert path in spec["paths"], f"route {path} đã cài đặt nhưng thiếu trong openapi.yaml"
        for method, op in methods.items():
            assert method in spec["paths"][path], f"{method.upper()} {path} thiếu trong spec"
            assert set(op["responses"]) <= set(spec["paths"][path][method]["responses"])
            checked += 1
    assert checked >= 1
    mine = implemented["components"]["schemas"]["HealthResponse"]
    contract = spec["components"]["schemas"]["HealthResponse"]
    assert set(mine["properties"]) == set(contract["properties"])
    assert set(mine["required"]) == set(contract["required"])
