"""异步任务轮询。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.api.deps import current_user
from backend.app.db import get_db
from backend.app.models.user import AgentTask, User
from backend.app.skills import SKILL_RUNNERS

router = APIRouter(tags=["tasks"])


class CreateTaskBody(BaseModel):
    skill_code: str
    project_id: str | None = None
    input: dict = Field(default_factory=dict)
    async_mode: bool = False


@router.post("/agent-tasks")
def create_task(body: CreateTaskBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    skill = body.skill_code if body.skill_code == "polish" else body.skill_code.upper()
    runner = SKILL_RUNNERS.get(skill)
    if not runner:
        raise HTTPException(status_code=400, detail={"code": "SKILL_NOT_FOUND", "message": f"未登记 {body.skill_code}"})

    task = AgentTask(
        id=uuid.uuid4().hex,
        user_id=user.id,
        project_id=body.project_id,
        skill_code=skill,
        status="running",
        input_summary=str(body.input)[:500],
        created_at=datetime.now(timezone.utc),
    )
    db.add(task)
    db.commit()

    # 当前同步执行；超过阈值的长任务后续切 Celery
    result = runner(body.input)
    task.status = "succeeded" if result.status == "succeeded" else "failed"
    task.result = result.model_dump()
    task.error = result.error
    task.finished_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "code": "OK",
        "message": "ok",
        "data": {
            "id": task.id,
            "status": task.status,
            "skill_code": task.skill_code,
            "result": task.result,
            "error": task.error,
        },
    }


@router.get("/agent-tasks/{task_id}")
def get_task(task_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = db.get(AgentTask, task_id)
    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "任务不存在"})
    return {
        "code": "OK",
        "message": "ok",
        "data": {
            "id": task.id,
            "status": task.status,
            "skill_code": task.skill_code,
            "project_id": task.project_id,
            "result": task.result,
            "error": task.error,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        },
    }
