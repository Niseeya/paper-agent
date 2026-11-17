"""S4 多篇对比：2～8 篇已索引论文 -> 带证据的对比结果。空缺填「库内未找到」。"""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db import SessionLocal
from backend.app.models import KnowledgeChunk, Paper
from backend.app.skills.base import SkillRequest, SkillResult

MISSING = "库内未找到"
UNRECOGNIZED = "原文未识别"


class S4Input(BaseModel):
    paper_ids: list[str] = Field(min_length=2, max_length=8)
    dimensions: list[str] = Field(
        default_factory=lambda: ["研究对象", "方法", "主要结论", "研究局限"]
    )

    @field_validator("paper_ids")
    @classmethod
    def unique_ids(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("paper_ids 不能重复")
        return v


class EvidenceCell(BaseModel):
    value: str
    paper_id: str
    page_start: int | None = None
    page_end: int | None = None
    snippet: str = ""


class DimensionRow(BaseModel):
    dimension: str
    cells: list[EvidenceCell]


class S4Output(BaseModel):
    papers: list[dict[str, Any]]
    matrix: list[DimensionRow]


_DIM_HINTS = {
    "研究对象": ["研究", "对象", "聚焦", "针对", "本文", "以"],
    "方法": ["方法", "路径", "框架", "视角", "分析", "采用"],
    "主要结论": ["结论", "认为", "表明", "发现", "因此", "可见"],
    "研究局限": ["局限", "不足", "有待", "尚未", "问题"],
}


def _best_snippet(chunks: list[KnowledgeChunk], hints: list[str]) -> tuple[str, int | None, int | None]:
    if not chunks:
        return MISSING, None, None
    best = None
    best_score = 0
    for ch in chunks:
        score = sum(1 for h in hints if h in ch.content)
        if score > best_score:
            best_score = score
            best = ch
    if not best or best_score == 0:
        # 没有命中维度词：标原文未识别，仍附首段便于人工查看
        first = chunks[0]
        return UNRECOGNIZED, first.page_start, first.page_end
    return first_sentence(best.content), best.page_start, best.page_end


def first_sentence(text: str, limit: int = 160) -> str:
    t = " ".join(text.split())
    for sep in ("。", "！", "？", ".", "!", "?"):
        if sep in t:
            t = t.split(sep, 1)[0] + sep
            break
    return t[:limit]


def compare_papers(db: Session, paper_ids: list[str], dimensions: list[str]) -> S4Output:
    papers_meta: list[dict[str, Any]] = []
    chunk_map: dict[str, list[KnowledgeChunk]] = {}
    for pid in paper_ids:
        paper = db.get(Paper, pid)
        if not paper or paper.status != "indexed" or not paper.is_public:
            papers_meta.append(
                {
                    "paper_id": pid,
                    "title": MISSING,
                    "authors": [],
                    "year": None,
                    "available": False,
                }
            )
            chunk_map[pid] = []
            continue
        papers_meta.append(
            {
                "paper_id": paper.id,
                "title": paper.title,
                "authors": list(paper.authors or []),
                "year": paper.publication_year,
                "available": True,
            }
        )
        chunk_map[pid] = list(
            db.scalars(
                select(KnowledgeChunk)
                .where(KnowledgeChunk.paper_id == pid)
                .order_by(KnowledgeChunk.chunk_index.asc())
                .limit(30)
            ).all()
        )

    matrix: list[DimensionRow] = []
    for dim in dimensions:
        hints = _DIM_HINTS.get(dim, [dim])
        cells: list[EvidenceCell] = []
        for pid in paper_ids:
            meta = next(p for p in papers_meta if p["paper_id"] == pid)
            if not meta["available"]:
                cells.append(EvidenceCell(value=MISSING, paper_id=pid))
                continue
            value, ps, pe = _best_snippet(chunk_map[pid], hints)
            snippet = ""
            if chunk_map[pid] and value not in (MISSING,):
                # 证据原文截断
                for ch in chunk_map[pid]:
                    if ps is not None and ch.page_start == ps:
                        snippet = ch.content[:200]
                        break
            cells.append(
                EvidenceCell(
                    value=value,
                    paper_id=pid,
                    page_start=ps,
                    page_end=pe,
                    snippet=snippet,
                )
            )
        matrix.append(DimensionRow(dimension=dim, cells=cells))
    return S4Output(papers=papers_meta, matrix=matrix)


def run_s4(req: SkillRequest | dict[str, Any], db: Session | None = None) -> SkillResult:
    started = time.perf_counter()
    if isinstance(req, dict):
        req = SkillRequest(skill_code="S4", input=req)
    try:
        payload = S4Input.model_validate(req.input)
    except ValidationError as exc:
        return SkillResult(
            skill_code="S4",
            status="failed",
            error=f"输入校验失败: {exc}",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    owns = db is None
    session = db or SessionLocal()
    try:
        out = compare_papers(session, payload.paper_ids, payload.dimensions)
        evidence = []
        for row in out.matrix:
            for cell in row.cells:
                if cell.page_start is not None and cell.value not in (MISSING,):
                    evidence.append(
                        {
                            "paper_id": cell.paper_id,
                            "dimension": row.dimension,
                            "page_start": cell.page_start,
                            "page_end": cell.page_end,
                        }
                    )
        return SkillResult(
            skill_code="S4",
            status="succeeded",
            data=out.model_dump(),
            evidence_refs=evidence,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        return SkillResult(
            skill_code="S4",
            status="failed",
            error=str(exc),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    finally:
        if owns:
            session.close()
