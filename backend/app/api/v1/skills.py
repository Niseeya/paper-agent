"""Skill 调试入口（后续由工作流接管）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.app.api.deps import current_user
from backend.app.models.user import User
from backend.app.skills import SKILL_RUNNERS

router = APIRouter(prefix="/skills", tags=["skills"])


class SkillInvokeBody(BaseModel):
    skill_code: str
    input: dict = Field(default_factory=dict)


@router.post("/invoke")
def invoke_skill(body: SkillInvokeBody, user: User = Depends(current_user)):
    _ = user
    code = "polish" if body.skill_code.lower() == "polish" else body.skill_code.upper()
    runner = SKILL_RUNNERS.get(code)
    if not runner:
        return {
            "code": "SKILL_NOT_FOUND",
            "message": f"未登记 Skill: {body.skill_code}",
            "data": None,
        }
    result = runner(body.input)
    return {
        "code": "OK" if result.status == "succeeded" else "SKILL_FAILED",
        "message": result.error or "ok",
        "data": result.model_dump(),
    }
