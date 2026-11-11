import sqlite3
import warnings
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

import app.models  # noqa: F401
from alembic import command
from app.core.database import Base
from tests.conftest import alembic_config

TABLES = {
    "users",
    "courses",
    "topics",
    "assessments",
    "results",
    "study_sessions",
    "recommendations",
}
REFERENCE_SQL = Path(__file__).resolve().parents[2] / "docs" / "03-api" / "schema.sql"


def test_upgrade_creates_all_tables_and_downgrade_removes_them(db_url):
    cfg = alembic_config(db_url)
    command.upgrade(cfg, "head")
    engine = create_engine(db_url)
    assert TABLES <= set(inspect(engine).get_table_names())
    command.downgrade(cfg, "base")
    assert TABLES.isdisjoint(inspect(engine).get_table_names())
    command.upgrade(cfg, "head")  # chạy lại được
    assert TABLES <= set(inspect(engine).get_table_names())
    engine.dispose()


@pytest.mark.filterwarnings("ignore:autogenerate skipping")
def test_models_and_migration_are_in_sync(migrated_engine):
    """Nếu sửa model mà quên tạo migration, test này sẽ fail."""
    with migrated_engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": True})
        assert compare_metadata(ctx, Base.metadata) == []


def test_expression_index_exists_because_autogenerate_cannot_see_it(migrated_engine):
    with migrated_engine.connect() as conn:
        sql = conn.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE name = 'uq_recs_current'"
        ).scalar()
    assert sql and "COALESCE(assessment_id, 0)" in sql and "WHERE is_current = 1" in sql


# --------------------------------------------------------------------------------------
# Đối chiếu migration với bản tham chiếu docs/03-api/schema.sql (cấu trúc + hành vi)
# --------------------------------------------------------------------------------------
def _describe(path) -> dict:
    conn = sqlite3.connect(path)
    out = {}
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT IN ('alembic_version', 'sqlite_sequence')"
        )
    ]
    for t in sorted(tables):
        cols = []
        for _cid, name, typ, notnull, default, pk in conn.execute(f"PRAGMA table_info({t})"):
            typ = typ.upper().replace("BOOLEAN", "INTEGER")
            default = None if default is None else default.strip("()").replace(" ", "").lower()
            notnull = 1 if pk else notnull  # INTEGER PRIMARY KEY không bao giờ NULL
            cols.append((name, typ, notnull, default, pk))
        fks = sorted(
            (r[3], r[2], r[4], r[6]) for r in conn.execute(f"PRAGMA foreign_key_list({t})")
        )
        idx = []
        for r in conn.execute(f"PRAGMA index_list({t})"):
            name, unique, origin, partial = r[1], r[2], r[3], r[4]
            if origin == "pk":
                continue
            idx_cols = tuple(c[2] for c in conn.execute(f"PRAGMA index_info({name})"))
            idx.append((unique, idx_cols, partial))
        autoinc = (
            "AUTOINCREMENT"
            in conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (t,))
            .fetchone()[0]
            .upper()
        )
        out[t] = {"cols": cols, "fks": fks, "idx": sorted(idx, key=repr), "autoinc": autoinc}
    conn.close()
    return out


@pytest.mark.skipif(not REFERENCE_SQL.exists(), reason="không thấy docs/03-api/schema.sql")
def test_migration_matches_reference_schema(db_url, tmp_path):
    command.upgrade(alembic_config(db_url), "head")
    ref_path = tmp_path / "reference.db"
    conn = sqlite3.connect(ref_path)
    conn.executescript(REFERENCE_SQL.read_text(encoding="utf-8"))
    conn.close()

    migrated = _describe(db_url.removeprefix("sqlite:///"))
    reference = _describe(ref_path)
    assert migrated.keys() == reference.keys()
    for table in reference:
        assert migrated[table] == reference[table], f"bảng {table} khác bản tham chiếu"


SETUP = """
INSERT INTO users(username,password_hash,display_name) VALUES('sv01','x','SV');
INSERT INTO courses(code,name,start_date,total_weeks) VALUES('D','M','2026-11-09',6);
INSERT INTO topics(course_id,name,order_no) VALUES (1,'A',1);
INSERT INTO assessments(topic_id,title,week_no,total_questions) VALUES (1,'BT1',1,10);
INSERT INTO results(user_id,assessment_id,score,wrong_count,completed_at)
  VALUES (1,1,5,5,'2026-11-10T08:00:00.000Z');
INSERT INTO recommendations(user_id,topic_id,type,rank,priority_score,reason_text,evidence_json)
  VALUES (1,1,'review_topic',1,1,'x','{"reasons":[{"code":"a"}]}');
"""
MUST_FAIL = [
    "INSERT INTO results(user_id,assessment_id,attempt_no,score,wrong_count,completed_at) VALUES (1,1,1,5,5,'2026-11-12T00:00:00.000Z')",
    "INSERT INTO results(user_id,assessment_id,score,wrong_count,completed_at) VALUES (99,1,5,5,'2026-11-12T00:00:00.000Z')",
    "INSERT INTO results(user_id,assessment_id,attempt_no,score,wrong_count,completed_at) VALUES (1,1,2,-1,0,'2026-11-12T00:00:00.000Z')",
    "INSERT INTO recommendations(user_id,topic_id,type,rank,priority_score,reason_text,evidence_json) VALUES (1,1,'practice_more',0,1,'x','{\"reasons\":[{\"code\":\"a\"}]}')",
    "INSERT INTO recommendations(user_id,topic_id,type,rank,priority_score,reason_text,evidence_json) VALUES (1,1,'practice_more',3,1,'x','{\"reasons\":\"low_average\"}')",
    "INSERT INTO results(user_id,assessment_id,attempt_no,score,wrong_count,started_at,completed_at) VALUES (1,1,3,1,1,'2026-11-13T00:00:00.000Z','2026-11-12T00:00:00.000Z')",
    "INSERT INTO recommendations(user_id,topic_id,type,rank,priority_score,reason_text,evidence_json) VALUES (1,1,'review_topic',2,1,'x','{\"reasons\":[]}')",
    "INSERT INTO recommendations(user_id,topic_id,type,rank,priority_score,reason_text,evidence_json) VALUES (1,1,'review_topic',2,1,'x','not json')",
    "INSERT INTO recommendations(user_id,topic_id,type,rank,priority_score,reason_text,evidence_json) VALUES (1,1,'practice_more',3,1,'x','{}')",
    "INSERT INTO recommendations(user_id,topic_id,type,rank,priority_score,reason_text,evidence_json) VALUES (1,1,'practice_more',3,1,'x','{\"metrics\":{}}')",
    "INSERT INTO recommendations(user_id,topic_id,type,rank,priority_score,reason_text,evidence_json,status) VALUES (1,1,'practice_more',2,1,'x','{\"reasons\":[{\"code\":\"a\"}]}','bad')",
    "INSERT INTO recommendations(user_id,topic_id,type,rank,priority_score,reason_text,evidence_json) VALUES (1,1,'review_topic',2,1,'dup','{\"reasons\":[{\"code\":\"a\"}]}')",
    "INSERT INTO users(username,password_hash,display_name) VALUES('SV01','x','trùng tên')",
    "INSERT INTO study_sessions(user_id,course_id,started_at,duration_seconds) VALUES (1,1,'2026-11-10T07:00:00.000Z',0)",
    "INSERT INTO assessments(topic_id,title,week_no,total_questions) VALUES (1,'BT2',0,10)",
    "INSERT INTO topics(course_id,name,order_no) VALUES (1,'B',1)",
]


@pytest.mark.skipif(not REFERENCE_SQL.exists(), reason="không thấy docs/03-api/schema.sql")
def test_migration_and_reference_reject_the_same_bad_data(db_url, tmp_path):
    command.upgrade(alembic_config(db_url), "head")
    ref_path = tmp_path / "reference.db"
    ref = sqlite3.connect(ref_path)
    ref.executescript(REFERENCE_SQL.read_text(encoding="utf-8"))
    ref.close()

    for _label, path in (("migration", db_url.removeprefix("sqlite:///")), ("reference", ref_path)):
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SETUP)
        for stmt in MUST_FAIL:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(stmt)
            conn.rollback()
        conn.close()
        warnings.simplefilter("default")
