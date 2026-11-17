"""S2 文献检索：关键词 + 混合检索（向量 + Reranker）。

独立测试要求：中英文关键词返回库内真实来源。
产品路径：mode=hybrid 时必须走向量与重排序；缺向量/模型则明确失败。
"""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db import SessionLocal
from backend.app.models import KnowledgeChunk, Paper
from backend.app.services.retrieval import evidence_to_paper_hits, hybrid_retrieve, score_text
from backend.app.skills.base import SkillRequest, SkillResult


class S2Input(BaseModel):
    query: str
    language: str = "all"  # all | zh | en
    top_k: int = Field(default=8, ge=1, le=20)
    # keyword：仅关键词（独立测试/无向量时）
    # hybrid：关键词+向量+强制 Reranker
    mode: str = "hybrid"


class PaperHit(BaseModel):
    paper_id: str
    title: str
    authors: list[str]
    year: int | None
    source: str = "public_kb"
    snippet: str = ""
    page_start: int | None = None
    page_end: int | None = None
    score: float = 0.0


class S2Output(BaseModel):
    query: str
    language: str
    mode: str
    papers: list[PaperHit]
    retrieval_meta: dict[str, Any] = Field(default_factory=dict)


def _title_language(title: str) -> str:
    """题名含汉字视为中文，否则视为英文（含其他拉丁文）。"""
    return "zh" if any("\u4e00" <= ch <= "\u9fff" for ch in title or "") else "en"


def filter_hits_by_language(hits: list[PaperHit], language: str) -> list[PaperHit]:
    lang = (language or "all").lower()
    if lang in ("", "all", "any", "*"):
        return hits
    if lang not in ("zh", "en"):
        return hits
    return [h for h in hits if _title_language(h.title) == lang]


def keyword_search(db: Session, query: str, top_k: int = 8) -> list[PaperHit]:
    papers = list(
        db.scalars(select(Paper).where(Paper.status == "indexed", Paper.is_public.is_(True))).all()
    )
    if not papers:
        return []

    hits: list[PaperHit] = []
    for paper in papers:
        meta_blob = " ".join(
            [paper.title or "", " ".join(paper.authors or []), paper.abstract or ""]
        )
        best_score = score_text(query, meta_blob)
        best_snippet = (paper.abstract or paper.title or "")[:240]
        best_page: tuple[int | None, int | None] = (None, None)

        chunks = list(
            db.scalars(
                select(KnowledgeChunk)
                .where(KnowledgeChunk.paper_id == paper.id)
                .order_by(KnowledgeChunk.chunk_index.asc())
                .limit(40)
            ).all()
        )
        for ch in chunks:
            s = score_text(query, ch.content)
            if s > best_score:
                best_score = s
                best_snippet = ch.content[:240]
                best_page = (ch.page_start, ch.page_end)

        if best_score <= 0:
            continue
        if best_page[0] is None and chunks:
            best_page = (chunks[0].page_start, chunks[0].page_end)
            if not best_snippet:
                best_snippet = chunks[0].content[:240]
        hits.append(
            PaperHit(
                paper_id=paper.id,
                title=paper.title,
                authors=list(paper.authors or []),
                year=paper.publication_year,
                source="public_kb",
                snippet=best_snippet,
                page_start=best_page[0],
                page_end=best_page[1],
                score=best_score,
            )
        )

    hits.sort(key=lambda x: x.score, reverse=True)
    return hits[:top_k]


def run_s2(req: SkillRequest | dict[str, Any], db: Session | None = None) -> SkillResult:
    started = time.perf_counter()
    if isinstance(req, dict):
        req = SkillRequest(skill_code="S2", input=req)
    try:
        payload = S2Input.model_validate(req.input)
    except ValidationError as exc:
        return SkillResult(
            skill_code="S2",
            status="failed",
            error=f"输入校验失败: {exc}",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    owns_session = db is None
    session = db or SessionLocal()
    try:
        meta: dict[str, Any] = {}
        # 指定语言时多取一些再过滤，尽量凑满 top_k
        fetch_k = payload.top_k if payload.language in ("all", "", "any") else min(20, max(payload.top_k * 3, payload.top_k))
        if payload.mode == "keyword":
            papers = keyword_search(session, payload.query, fetch_k)
        else:
            evidence, meta = hybrid_retrieve(session, payload.query, top_k=fetch_k)
            papers = [PaperHit.model_validate(x) for x in evidence_to_paper_hits(evidence, fetch_k)]

        papers = filter_hits_by_language(papers, payload.language)[: payload.top_k]
        meta = {**meta, "language_filter": payload.language}

        for p in papers:
            assert p.paper_id and p.title
        out = S2Output(
            query=payload.query,
            language=payload.language,
            mode=payload.mode,
            papers=papers,
            retrieval_meta=meta,
        )
        warnings: list[str] = []
        if not papers:
            warnings.append("公用知识库没有相关已索引论文或关键词未命中")
        return SkillResult(
            skill_code="S2",
            status="succeeded",
            data=out.model_dump(),
            evidence_refs=[
                {
                    "paper_id": p.paper_id,
                    "title": p.title,
                    "page_start": p.page_start,
                    "page_end": p.page_end,
                }
                for p in papers
            ],
            warnings=warnings,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        return SkillResult(
            skill_code="S2",
            status="failed",
            error=str(exc),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    finally:
        if owns_session:
            session.close()
