"""S5 方向分类：一组已索引论文 -> 研究方向分类，每类列出依据论文。"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db import SessionLocal
from backend.app.models import Paper
from backend.app.skills.base import SkillRequest, SkillResult

# 领域预置方向词（影视/青春电影语料）；未命中归入「其他方向」
DIRECTION_LEXICON: list[tuple[str, list[str]]] = [
    ("青春电影与青年形象", ["青春", "青年", "校园", "成长"]),
    ("叙事与影像美学", ["叙事", "影像", "美学", "视像", "镜头", "风格"]),
    ("类型与产业", ["类型", "票房", "市场", "产业", "贺岁", "消费"]),
    ("文化与意识形态", ["文化", "意识形态", "价值观", "怀旧", "时代"]),
    ("性别与身份", ["女性", "性别", "身份", "主体"]),
]
OTHER_DIRECTION = "其他方向"


class S5Input(BaseModel):
    paper_ids: list[str] = Field(default_factory=list, max_length=200)
    # 为空则对公用库已索引论文分类（上限 200）


class DirectionGroup(BaseModel):
    direction: str
    paper_ids: list[str]
    titles: list[str]
    rationale: str


class S5Output(BaseModel):
    directions: list[DirectionGroup]
    uncategorized: list[str] = Field(default_factory=list)


def score_title(title: str, keywords: list[str]) -> int:
    return sum(1 for k in keywords if k in title)


def assign_direction(title: str) -> str:
    """按题名关键词归入方向；无命中则「其他方向」。"""
    best_dir = OTHER_DIRECTION
    best_score = 0
    for name, kws in DIRECTION_LEXICON:
        s = score_title(title or "", kws)
        if s > best_score:
            best_score = s
            best_dir = name
    return best_dir if best_score > 0 else OTHER_DIRECTION


def classify_papers(db: Session, paper_ids: list[str]) -> S5Output:
    if paper_ids:
        papers = [db.get(Paper, pid) for pid in paper_ids]
        papers = [p for p in papers if p and p.status == "indexed" and p.is_public]
    else:
        papers = list(
            db.scalars(
                select(Paper)
                .where(Paper.status == "indexed", Paper.is_public.is_(True))
                .order_by(Paper.indexed_at.desc())
                .limit(200)
            ).all()
        )

    buckets: dict[str, list[Paper]] = defaultdict(list)
    for paper in papers:
        buckets[assign_direction(paper.title or "")].append(paper)

    directions: list[DirectionGroup] = []
    for name, kws in DIRECTION_LEXICON:
        items = buckets.get(name) or []
        if not items:
            continue
        directions.append(
            DirectionGroup(
                direction=name,
                paper_ids=[p.id for p in items],
                titles=[p.title for p in items],
                rationale=f"题名命中关键词：{'、'.join(kws)}",
            )
        )
    other = buckets.get(OTHER_DIRECTION) or []
    if other:
        directions.append(
            DirectionGroup(
                direction=OTHER_DIRECTION,
                paper_ids=[p.id for p in other],
                titles=[p.title for p in other],
                rationale="题名未稳定命中预置方向词，归入其他，供人工调整",
            )
        )
    return S5Output(directions=directions, uncategorized=[])


def run_s5(req: SkillRequest | dict[str, Any], db: Session | None = None) -> SkillResult:
    started = time.perf_counter()
    if isinstance(req, dict):
        req = SkillRequest(skill_code="S5", input=req)
    try:
        payload = S5Input.model_validate(req.input or {})
    except ValidationError as exc:
        return SkillResult(
            skill_code="S5",
            status="failed",
            error=f"输入校验失败: {exc}",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    owns = db is None
    session = db or SessionLocal()
    try:
        out = classify_papers(session, payload.paper_ids)
        if not out.directions:
            return SkillResult(
                skill_code="S5",
                status="failed",
                error="公用知识库没有可分类的已索引论文",
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        return SkillResult(
            skill_code="S5",
            status="succeeded",
            data=out.model_dump(),
            evidence_refs=[
                {"direction": d.direction, "paper_ids": d.paper_ids} for d in out.directions
            ],
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        return SkillResult(
            skill_code="S5",
            status="failed",
            error=str(exc),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    finally:
        if owns:
            session.close()
