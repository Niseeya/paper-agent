"""Skill 统一请求/结果结构。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SkillRequest(BaseModel):
    task_id: str | None = None
    project_id: str | None = None
    skill_code: str
    input: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)


class SkillResult(BaseModel):
    skill_code: str
    status: str
    data: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    model_id: str | None = None
    prompt_version: str | None = None
    usage: dict[str, int] = Field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})
    duration_ms: int = 0
