"""公用知识库：列表、上传、删除。"""

from __future__ import annotations

import tempfile
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.app.api.deps import current_user
from backend.app.db import get_db
from backend.app.models import DocumentFile, KnowledgeChunk, Paper
from backend.app.models.embedding import ChunkEmbedding
from backend.app.models.user import User
from backend.app.services.paper_ingest import IngestError, ingest_pdf
from backend.app.skills.s5_classify import (
    DIRECTION_LEXICON,
    OTHER_DIRECTION,
    assign_direction,
)

router = APIRouter(prefix="/papers", tags=["papers"])


def _paper_brief(p: Paper) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "authors": p.authors,
        "year": p.publication_year,
        "source_type": p.source_type,
        "status": p.status,
        "page_count": p.page_count,
        "section_recognized": p.section_recognized,
        "uploader_id": p.uploader_id,
        "direction": assign_direction(p.title or ""),
    }


@router.get("")
def list_papers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    q: str | None = None,
    direction: str | None = Query(None, description="研究方向筛选，与 S5 方向名一致"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    _ = user
    stmt = select(Paper).where(Paper.status == "indexed", Paper.is_public.is_(True))
    if q:
        stmt = stmt.where(Paper.title.like(f"%{q}%"))

    # 方向筛选：先取候选再按 assign_direction 精确归属，避免一词多向误入
    if direction:
        known = {name for name, _ in DIRECTION_LEXICON} | {OTHER_DIRECTION}
        if direction not in known:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_DIRECTION", "message": f"未知方向：{direction}"},
            )
        candidates = list(db.scalars(stmt.order_by(Paper.indexed_at.desc())).all())
        matched = [p for p in candidates if assign_direction(p.title or "") == direction]
        total = len(matched)
        start = (page - 1) * page_size
        rows = matched[start : start + page_size]
    else:
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = list(
            db.scalars(
                stmt.order_by(Paper.indexed_at.desc()).offset((page - 1) * page_size).limit(page_size)
            ).all()
        )

    return {
        "code": "OK",
        "message": "ok",
        "data": {
            "items": [_paper_brief(p) for p in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
            "direction": direction,
        },
    }


@router.get("/directions")
def list_directions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """公用库方向汇总：供知识库页筛选（含每向篇数与样例题名）。"""
    _ = user
    papers = list(
        db.scalars(
            select(Paper)
            .where(Paper.status == "indexed", Paper.is_public.is_(True))
            .order_by(Paper.indexed_at.desc())
        ).all()
    )
    buckets: dict[str, list[Paper]] = defaultdict(list)
    for p in papers:
        buckets[assign_direction(p.title or "")].append(p)

    directions = []
    for name, kws in DIRECTION_LEXICON:
        items = buckets.get(name) or []
        if not items:
            continue
        directions.append(
            {
                "direction": name,
                "count": len(items),
                "keywords": kws,
                "sample_titles": [p.title for p in items[:5]],
            }
        )
    other = buckets.get(OTHER_DIRECTION) or []
    if other:
        directions.append(
            {
                "direction": OTHER_DIRECTION,
                "count": len(other),
                "keywords": [],
                "sample_titles": [p.title for p in other[:5]],
            }
        )
    return {
        "code": "OK",
        "message": "ok",
        "data": {
            "total": len(papers),
            "directions": directions,
        },
    }


@router.post("/upload")
async def upload_paper(
    file: UploadFile = File(...),
    rights_confirmed: bool = Form(False),
    embed: bool = Form(True),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail={"code": "PAPER_FILE_INVALID", "message": "只接受 PDF"})
    suffix = Path(file.filename).suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        data = ingest_pdf(
            db,
            src_path=tmp_path,
            file_name=file.filename,
            uploader_id=user.id,
            rights_confirmed=rights_confirmed,
            embed=embed,
        )
        return {"code": "OK", "message": "已索引并进入公用知识库", "data": data}
    except IngestError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message}) from exc
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/{paper_id}")
def get_paper(paper_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _ = user
    paper = db.get(Paper, paper_id)
    if not paper or paper.status != "indexed" or not paper.is_public:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "论文不存在或未索引"})
    return {
        "code": "OK",
        "message": "ok",
        "data": {
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.publication_year,
            "abstract": paper.abstract,
            "source_type": paper.source_type,
            "section_tree": paper.section_tree,
            "section_recognized": paper.section_recognized,
            "page_count": paper.page_count,
            "uploader_id": paper.uploader_id,
        },
    }


@router.delete("/{paper_id}")
def delete_paper(paper_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "论文不存在"})
    if paper.is_preset:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "不能删除预置论文"})
    if paper.uploader_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "只能删除本人上传的论文"})

    db.execute(delete(ChunkEmbedding).where(ChunkEmbedding.paper_id == paper_id))
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.paper_id == paper_id))
    db.execute(delete(DocumentFile).where(DocumentFile.paper_id == paper_id))
    db.delete(paper)
    db.commit()
    return {"code": "OK", "message": "已删除文件、切片与向量", "data": {"id": paper_id}}
