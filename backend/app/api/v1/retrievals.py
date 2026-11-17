"""项目检索与问答入口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.api.deps import current_user
from backend.app.db import get_db
from backend.app.models.user import Project, User
from backend.app.skills.s2_retrieve import run_s2

router = APIRouter(prefix="/projects", tags=["retrievals"])


class RetrievalBody(BaseModel):
    query: str = Field(min_length=1)
    language: str = Field(default="all", pattern="^(all|zh|en)$")
    top_k: int = Field(default=8, ge=1, le=20)
    mode: str = "hybrid"


def _owned(db: Session, user: User, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "项目不存在"})
    return project


@router.post("/{project_id}/retrievals")
def create_retrieval(
    project_id: str,
    body: RetrievalBody,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    _owned(db, user, project_id)
    result = run_s2(
        {
            "query": body.query,
            "language": body.language,
            "top_k": body.top_k,
            "mode": body.mode,
        },
        db=db,
    )
    if result.status != "succeeded":
        code = "EVIDENCE_INSUFFICIENT" if "向量" in (result.error or "") else "SKILL_FAILED"
        if "没有相关" in " ".join(result.warnings):
            code = "EVIDENCE_INSUFFICIENT"
        raise HTTPException(status_code=400, detail={"code": code, "message": result.error or "检索失败"})
    return {"code": "OK", "message": "ok", "data": result.model_dump()}
