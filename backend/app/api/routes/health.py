from datetime import UTC, datetime

from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession
from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Kiểm tra tình trạng hệ thống",
    responses={503: {"model": HealthResponse, "description": "Không kết nối được cơ sở dữ liệu"}},
)
def health(response: Response, db: DbSession) -> HealthResponse:
    """Trả 200 nếu API và cơ sở dữ liệu hoạt động, 503 nếu DB lỗi.

    Không trả chi tiết lỗi hay đường dẫn DB ra ngoài (NFR06).
    """
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except SQLAlchemyError:
        database = "error"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        database=database,
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        time=datetime.now(UTC).isoformat(timespec="seconds"),
    )
