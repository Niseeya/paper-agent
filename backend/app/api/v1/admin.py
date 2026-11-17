"""管理端：项目、模型配置、提示词。普通用户不可见。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.deps import current_user
from backend.app.db import get_db
from backend.app.models.system_config import PromptVersion
from backend.app.models.user import Project, User
from backend.app.services import llm_settings as llm

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "需要管理员权限"})
    return user


@router.get("/projects")
def list_all_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ = user
    total = db.scalar(select(func.count()).select_from(Project)) or 0
    rows = list(
        db.scalars(
            select(Project).order_by(Project.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
    )
    owner_ids = {p.owner_id for p in rows}
    owners = {
        u.id: u
        for u in db.scalars(select(User).where(User.id.in_(owner_ids))).all()
    } if owner_ids else {}
    items = []
    for p in rows:
        owner = owners.get(p.owner_id)
        items.append(
            {
                "id": p.id,
                "title": p.title,
                "paper_type": p.paper_type,
                "status": p.status,
                "outline_confirmed": p.outline_confirmed,
                "owner_id": p.owner_id,
                "owner_name": (owner.display_name or owner.username) if owner else "",
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
        )
    return {
        "code": "OK",
        "message": "ok",
        "data": {"items": items, "page": page, "page_size": page_size, "total": total},
    }


class ChatModelBody(BaseModel):
    endpoint: str = Field(min_length=1, max_length=500)
    model_name: str = Field(min_length=1, max_length=120)
    # None/省略=不改；空串也不改；非空则更新
    api_key: str | None = None
    enabled: bool = True
    notes: str = ""


@router.get("/model-configs/chat")
def get_chat_model(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = user
    llm.seed_llm_settings(db)
    cfg = llm.get_active_model(db, "chat")
    if not cfg:
        return {"code": "OK", "message": "尚未配置", "data": None}
    return {"code": "OK", "message": "ok", "data": llm.model_public_view(cfg)}


@router.put("/model-configs/chat")
def put_chat_model(
    body: ChatModelBody,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cfg = llm.upsert_chat_model(
        db,
        endpoint=body.endpoint.strip(),
        model_name=body.model_name.strip(),
        api_key=body.api_key,
        enabled=body.enabled,
        notes=body.notes or "",
        user_id=user.id,
    )
    return {"code": "OK", "message": "模型配置已保存", "data": llm.model_public_view(cfg)}


@router.post("/model-configs/chat/test")
def test_chat_model(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = user
    adapter = llm.build_chat_adapter(db)
    if not adapter.available():
        raise HTTPException(
            status_code=400,
            detail={"code": "LLM_NOT_CONFIGURED", "message": "请先填写 endpoint、model 与 API Key"},
        )
    try:
        text = adapter.chat(
            [{"role": "user", "content": "只回复两个字：可用"}],
            temperature=0,
            max_tokens=16,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400,
            detail={"code": "LLM_TEST_FAILED", "message": str(exc)},
        ) from exc
    return {
        "code": "OK",
        "message": "连通成功",
        "data": {"model_id": adapter.model_id, "reply": text[:80]},
    }


@router.get("/prompts")
def list_prompts(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = user
    llm.seed_llm_settings(db)
    rows = list(
        db.scalars(
            select(PromptVersion)
            .where(PromptVersion.is_active.is_(True))
            .order_by(PromptVersion.skill_code.asc(), PromptVersion.prompt_key.asc())
        ).all()
    )
    return {
        "code": "OK",
        "message": "ok",
        "data": {"items": [llm.prompt_public_view(r) for r in rows]},
    }


class PromptBody(BaseModel):
    skill_code: str = Field(min_length=1, max_length=32)
    prompt_key: str = Field(default="system", max_length=64)
    title: str = ""
    content: str = Field(min_length=1)


@router.put("/prompts")
def put_prompt(
    body: PromptBody,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = llm.save_prompt(
        db,
        skill_code=body.skill_code.strip(),
        prompt_key=(body.prompt_key or "system").strip(),
        content=body.content,
        title=body.title or "",
        user_id=user.id,
    )
    return {"code": "OK", "message": "提示词已保存（新版本）", "data": llm.prompt_public_view(row)}
