"""注册、登录、退出、当前用户。"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import current_user
from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.db import get_db
from backend.app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


class RegisterBody(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    display_name: str = ""


class LoginBody(BaseModel):
    username: str
    password: str


def _user_view(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "display_name": u.display_name,
        "role": u.role,
    }


@router.post("/register")
def register(body: RegisterBody, db: Session = Depends(get_db)):
    exists = db.scalar(select(User).where(User.username == body.username))
    if exists:
        raise HTTPException(status_code=400, detail={"code": "USER_EXISTS", "message": "用户名已存在"})
    user = User(
        id=uuid.uuid4().hex,
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name or body.username,
        role="user",
    )
    db.add(user)
    db.commit()
    token = create_access_token(user.id, user.role)
    return {"code": "OK", "message": "注册成功", "data": {"token": token, "user": _user_view(user)}}


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username))
    now = datetime.now(timezone.utc)
    if user and user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=423,
            detail={"code": "LOCKED", "message": "连续登录失败，请 10 分钟后再试"},
        )
    if not user or not verify_password(body.password, user.password_hash):
        if user:
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= 5:
                user.locked_until = now + timedelta(minutes=10)
                user.failed_login_count = 0
            db.commit()
        raise HTTPException(status_code=401, detail={"code": "LOGIN_FAILED", "message": "用户名或密码错误"})
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()
    token = create_access_token(user.id, user.role)
    return {"code": "OK", "message": "登录成功", "data": {"token": token, "user": _user_view(user)}}


@router.post("/logout")
def logout(user: User = Depends(current_user)):
    # 无状态 JWT：客户端丢弃令牌即可
    return {"code": "OK", "message": "已退出", "data": {"user_id": user.id}}


@users_router.get("/me")
def me(user: User = Depends(current_user)):
    return {"code": "OK", "message": "ok", "data": _user_view(user)}


class PatchMeBody(BaseModel):
    display_name: str | None = None


@users_router.patch("/me")
def patch_me(body: PatchMeBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.display_name is not None:
        user.display_name = body.display_name
        db.commit()
    return {"code": "OK", "message": "ok", "data": _user_view(user)}
