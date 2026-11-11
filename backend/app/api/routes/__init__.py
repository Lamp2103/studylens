from fastapi import APIRouter

from app.api.routes import health

api_router = APIRouter()
api_router.include_router(health.router)

# Các router tiếp theo (thêm dần theo từng tuần):
# api_router.include_router(auth.router)             # tuần 2: FR01, FR12
# api_router.include_router(dashboard.router)        # tuần 2: FR02
# api_router.include_router(topics.router)           # tuần 2: FR03
