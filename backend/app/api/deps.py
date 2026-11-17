"""鉴权依赖。"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.security import decode_token
from backend.app.db import get_db
from backend.app.models.user import User


def current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "需要登录"})
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "令牌无效"})
    user = db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "用户不可用"})
    return user
