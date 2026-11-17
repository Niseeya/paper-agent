"""项目 CRUD；状态只由业务动作改变。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.app.api.deps import current_user
from backend.app.db import get_db
from backend.app.models.project_content import ProjectArtifact
from backend.app.models.user import AgentTask, Project, User

router = APIRouter(prefix="/projects", tags=["projects"])

ALLOWED_TRANSITIONS = {
    "draft": {"preparing", "outline_pending"},
    "preparing": {"outline_pending", "draft"},
    "outline_pending": {"writing", "draft"},
    "writing": {"checking", "outline_pending"},
    "checking": {"exportable", "writing"},
    "exportable": {"writing"},
}


class CreateProjectBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    paper_type: str = "综述"


class PatchProjectBody(BaseModel):
    title: str | None = None
    paper_type: str | None = None
    # 禁止客户端直接指定 status


def _project_view(p: Project) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "paper_type": p.paper_type,
        "status": p.status,
        "outline_confirmed": p.outline_confirmed,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.get("")
def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Project).where(Project.owner_id == user.id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(Project.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
    )
    return {
        "code": "OK",
        "message": "ok",
        "data": {"items": [_project_view(p) for p in rows], "page": page, "page_size": page_size, "total": total},
    }


@router.post("")
def create_project(body: CreateProjectBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    project = Project(
        id=uuid.uuid4().hex,
        owner_id=user.id,
        title=body.title,
        paper_type=body.paper_type,
        status="draft",
        created_at=now,
        updated_at=now,
    )
    db.add(project)
    db.commit()
    return {"code": "OK", "message": "已创建", "data": _project_view(project)}


def _owned_project(db: Session, user: User, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "项目不存在"})
    return project


@router.get("/{project_id}")
def get_project(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"code": "OK", "message": "ok", "data": _project_view(_owned_project(db, user, project_id))}


@router.patch("/{project_id}")
def patch_project(
    project_id: str,
    body: PatchProjectBody,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _owned_project(db, user, project_id)
    if body.title is not None:
        project.title = body.title
    if body.paper_type is not None:
        project.paper_type = body.paper_type
    project.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"code": "OK", "message": "ok", "data": _project_view(project)}


@router.delete("/{project_id}")
def delete_project(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """仅管理员可删除项目及其大纲/正文/润色/核查/导出；不删除公用知识库论文。"""
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "仅管理员可删除项目"},
        )
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "项目不存在"})
    db.execute(delete(ProjectArtifact).where(ProjectArtifact.project_id == project_id))
    db.execute(delete(AgentTask).where(AgentTask.project_id == project_id))
    db.delete(project)
    db.commit()
    return {"code": "OK", "message": "已删除", "data": {"id": project_id}}
