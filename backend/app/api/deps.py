"""Các dependency dùng chung cho endpoint.

Tuần 2 sẽ thêm `get_current_user` (đọc JWT) ở đây.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

DbSession = Annotated[Session, Depends(get_db)]
