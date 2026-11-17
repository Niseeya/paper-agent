"""S9 论文检查：列出引用问题（L1/L2）与逻辑问题。"""

from __future__ import annotations

import re
import time
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from backend.app.db import SessionLocal
from backend.app.models import KnowledgeChunk, Paper
from backend.app.skills.base import SkillRequest, SkillResult
from sqlalchemy import select


class CitationRef(BaseModel):
    sentence: str
    paper_id: str | None = None
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    page_start: int | None = None
    evidence_snippet: str | None = None
    is_formal: bool = True


class S9Input(BaseModel):
    paragraphs: list[str] = Field(min_length=1)
    citations: list[CitationRef] = Field(default_factory=list)


class Issue(BaseModel):
    kind: str  # citation | logic
    sentence: str
    detail: str


class S9Output(BaseModel):
    citation_issues: list[Issue]
    logic_issues: list[Issue]
    passed: bool


def _l1_ok(paper: Paper | None, ref: CitationRef) -> bool:
    # 正式引用只能指向公用知识库已索引论文
    if not paper or paper.status != "indexed" or not getattr(paper, "is_public", True):
        return False
    if ref.title and ref.title.strip() and ref.title.strip() != paper.title.strip():
        # 允许题名高度一致的宽松：包含关系
        if ref.title not in paper.title and paper.title not in ref.title:
            return False
    if ref.year is not None and paper.publication_year is not None and ref.year != paper.publication_year:
        return False
    if ref.authors:
        paper_authors = set(paper.authors or [])
        if paper_authors and not set(ref.authors).intersection(paper_authors):
            return False
    return True


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def _l2_ok(db: Session, paper_id: str, snippet: str | None, page_start: int | None) -> bool:
    if not snippet or page_start is None:
        return False
    chunks = list(
        db.scalars(
            select(KnowledgeChunk).where(KnowledgeChunk.paper_id == paper_id).limit(80)
        ).all()
    )
    # 只用汉字与标点做回链，避免刊名拼音干扰
    cn = re.sub(r"[^\u4e00-\u9fff，。；：、《》？！“”‘’]", "", snippet or "")
    needle = cn[:36]
    if len(needle) < 10:
        needle = _norm_text(snippet)[:36]
    if len(needle) < 10:
        return False
    for ch in chunks:
        body_cn = re.sub(r"[^\u4e00-\u9fff，。；：、《》？！“”‘’]", "", ch.content or "")
        body = _norm_text(ch.content or "")
        if needle and (needle in body_cn or needle in body):
            return True
        short = needle[:16]
        if short and (short in body_cn or short in body):
            return True
    return False


def check_paper(db: Session, paragraphs: list[str], citations: list[CitationRef]) -> S9Output:
    citation_issues: list[Issue] = []
    logic_issues: list[Issue] = []

    for ref in citations:
        if not ref.is_formal:
            continue
        if not ref.paper_id:
            citation_issues.append(
                Issue(kind="citation", sentence=ref.sentence, detail="正式引用缺少论文标识（L1 失败）")
            )
            continue
        paper = db.get(Paper, ref.paper_id)
        if not _l1_ok(paper, ref):
            citation_issues.append(
                Issue(kind="citation", sentence=ref.sentence, detail="未通过 L1：题名/作者/年份与库内不一致或论文不可用")
            )
            continue
        if not _l2_ok(db, ref.paper_id, ref.evidence_snippet, ref.page_start):
            citation_issues.append(
                Issue(kind="citation", sentence=ref.sentence, detail="未通过 L2：未绑定可回链的证据片段或页码")
            )

    # 逻辑：明显重复句、缺少论据的判断句
    seen: dict[str, int] = {}
    for p in paragraphs:
        norm = re.sub(r"\s+", "", p)
        if len(norm) < 8:
            continue
        seen[norm] = seen.get(norm, 0) + 1
        if seen[norm] == 2:
            logic_issues.append(Issue(kind="logic", sentence=p[:120], detail="明显重复"))
        if re.search(r"(因此|可见|表明|证明|必须|必然).{0,20}$", p) or re.search(
            r"(因此|可见|表明|证明)", p
        ):
            if "[" not in p and "证据" not in p and not any(c.sentence == p for c in citations if c.is_formal):
                # 判断句且无引用标记
                if not any(c for c in citations if c.sentence and c.sentence[:20] in p):
                    logic_issues.append(Issue(kind="logic", sentence=p[:120], detail="缺少论据的判断句"))

    return S9Output(
        citation_issues=citation_issues,
        logic_issues=logic_issues,
        passed=not citation_issues and not logic_issues,
    )


def run_s9(req: SkillRequest | dict[str, Any], db: Session | None = None) -> SkillResult:
    started = time.perf_counter()
    if isinstance(req, dict):
        req = SkillRequest(skill_code="S9", input=req)
    try:
        payload = S9Input.model_validate(req.input)
    except ValidationError as exc:
        return SkillResult(
            skill_code="S9",
            status="failed",
            error=f"输入校验失败: {exc}",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    owns = db is None
    session = db or SessionLocal()
    try:
        out = check_paper(session, payload.paragraphs, payload.citations)
        return SkillResult(
            skill_code="S9",
            status="succeeded",
            data=out.model_dump(),
            warnings=[i.detail for i in out.citation_issues + out.logic_issues],
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        return SkillResult(
            skill_code="S9",
            status="failed",
            error=str(exc),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    finally:
        if owns:
            session.close()
