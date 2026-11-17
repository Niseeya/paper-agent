"""S6 研究空白：研究现状或论文组 -> 候选空白（类型=建议），附证据或标明证据不足。"""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db import SessionLocal
from backend.app.models import Paper
from backend.app.skills.base import SkillRequest, SkillResult
from backend.app.skills.s5_classify import DIRECTION_LEXICON, classify_papers

EVIDENCE_LACK = "证据不足"


class S6Input(BaseModel):
    research_status: str = ""
    paper_ids: list[str] = Field(default_factory=list, max_length=50)


class GapItem(BaseModel):
    statement: str
    type: str = "建议"
    evidence_status: str  # 有证据 | 证据不足
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)


class S6Output(BaseModel):
    gaps: list[GapItem]


def _direction_coverage(db: Session, paper_ids: list[str]) -> list[GapItem]:
    classified = classify_papers(db, paper_ids)
    covered = {d.direction for d in classified.directions if d.direction != "其他方向"}
    all_dirs = [name for name, _ in DIRECTION_LEXICON]
    gaps: list[GapItem] = []
    for name in all_dirs:
        if name not in covered:
            gaps.append(
                GapItem(
                    statement=f"库内已索引文献对「{name}」覆盖不足，可作为候选研究空白深入",
                    type="建议",
                    evidence_status=EVIDENCE_LACK,
                    evidence_refs=[],
                )
            )
        else:
            group = next(d for d in classified.directions if d.direction == name)
            if len(group.paper_ids) <= 1:
                gaps.append(
                    GapItem(
                        statement=f"「{name}」仅有少量文献支撑，存在深化空间",
                        type="建议",
                        evidence_status="有证据",
                        evidence_refs=[{"paper_id": pid, "title": title} for pid, title in zip(group.paper_ids, group.titles)],
                    )
                )
    return gaps


def _status_text_gaps(db: Session, text: str) -> list[GapItem]:
    """从用户描述的研究现状抽「尚未/缺乏/不足」句，并尝试在库内找支撑。"""
    gaps: list[GapItem] = []
    markers = ["尚未", "缺乏", "不足", "有待", "空白", "较少", "鲜有"]
    sentences = [s.strip() for s in text.replace("\n", "。").split("。") if s.strip()]
    for sent in sentences:
        if not any(m in sent for m in markers):
            continue
        # 在库内搜相关切片
        papers = list(
            db.scalars(select(Paper).where(Paper.status == "indexed", Paper.is_public.is_(True)).limit(40)).all()
        )
        refs: list[dict[str, Any]] = []
        for p in papers:
            if any(tok in (p.title or "") for tok in sent if len(tok) >= 2):
                refs.append({"paper_id": p.id, "title": p.title})
            if len(refs) >= 2:
                break
        # 简化：用二字词碰撞
        if not refs:
            tokens = [sent[i : i + 2] for i in range(0, min(len(sent), 20), 2)]
            for p in papers:
                if sum(1 for t in tokens if t and t in (p.title or "")) >= 2:
                    refs.append({"paper_id": p.id, "title": p.title})
                if len(refs) >= 2:
                    break
        gaps.append(
            GapItem(
                statement=sent[:120],
                type="建议",
                evidence_status="有证据" if refs else EVIDENCE_LACK,
                evidence_refs=refs,
            )
        )
    return gaps


def find_gaps(db: Session, research_status: str, paper_ids: list[str]) -> S6Output:
    gaps: list[GapItem] = []
    if research_status.strip():
        gaps.extend(_status_text_gaps(db, research_status.strip()))
    gaps.extend(_direction_coverage(db, paper_ids))
    # 去重 statement
    seen: set[str] = set()
    unique: list[GapItem] = []
    for g in gaps:
        if g.statement in seen:
            continue
        seen.add(g.statement)
        unique.append(g)
    if not unique:
        unique.append(
            GapItem(
                statement="当前输入与库内覆盖未能形成明确空白，建议补充研究现状描述或扩大论文集合",
                type="建议",
                evidence_status=EVIDENCE_LACK,
            )
        )
    return S6Output(gaps=unique[:12])


def run_s6(req: SkillRequest | dict[str, Any], db: Session | None = None) -> SkillResult:
    started = time.perf_counter()
    if isinstance(req, dict):
        req = SkillRequest(skill_code="S6", input=req)
    try:
        payload = S6Input.model_validate(req.input or {})
    except ValidationError as exc:
        return SkillResult(
            skill_code="S6",
            status="failed",
            error=f"输入校验失败: {exc}",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    owns = db is None
    session = db or SessionLocal()
    try:
        out = find_gaps(session, payload.research_status, payload.paper_ids)
        for g in out.gaps:
            assert g.type == "建议"
        return SkillResult(
            skill_code="S6",
            status="succeeded",
            data=out.model_dump(),
            evidence_refs=[ref for g in out.gaps for ref in g.evidence_refs],
            warnings=[g.statement for g in out.gaps if g.evidence_status == EVIDENCE_LACK],
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        return SkillResult(
            skill_code="S6",
            status="failed",
            error=str(exc),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    finally:
        if owns:
            session.close()
