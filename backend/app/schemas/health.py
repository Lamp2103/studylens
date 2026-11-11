from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "error"]
    app: str
    version: str
    environment: str
    time: str  # ISO 8601 UTC
