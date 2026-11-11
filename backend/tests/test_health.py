from sqlalchemy.exc import OperationalError

from app.core.database import engine, get_db
from app.main import app


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["environment"] == "test"
    assert body["app"] and body["version"] and body["time"]


def test_health_returns_503_when_database_fails(client):
    class BrokenSession:
        def execute(self, *_args, **_kwargs):
            raise OperationalError("SELECT 1", {}, Exception("boom"))

        def close(self):
            pass

    app.dependency_overrides[get_db] = lambda: BrokenSession()
    r = client.get("/health")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    assert body["database"] == "error"
    assert "boom" not in r.text  # không lộ chi tiết lỗi


def test_sqlite_foreign_keys_are_enabled():
    with engine.connect() as conn:
        assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1


def test_cors_allows_frontend_origin(client):
    r = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_openapi_docs_available(client):
    assert client.get("/docs").status_code == 200
    assert "/health" in client.get("/openapi.json").json()["paths"]
