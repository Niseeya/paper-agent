"""混合检索：关键词 + 向量 → 去重 → Reranker。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.app.adapters.embedding import EmbeddingAdapter, get_embedding_adapter
from backend.app.adapters.reranker import RerankerAdapter, get_reranker_adapter
from backend.app.db import DATABASE_URL
from backend.app.models import KnowledgeChunk, Paper
from backend.app.models.embedding import ChunkEmbedding
from backend.app.services.vector_math import cosine_similarity


@dataclass
class EvidenceHit:
    chunk_id: str
    paper_id: str
    title: str
    authors: list[str]
    year: int | None
    content: str
    page_start: int
    page_end: int
    score: float
    source_channel: str  # keyword | vector | hybrid


def score_text(query: str, text_value: str) -> float:
    q = query.lower().strip()
    if not q or not text_value:
        return 0.0
    t = text_value.lower()
    score = 0.0
    if q in t:
        score += 5.0
    for token in [x for x in q.replace("/", " ").replace("-", " ").split() if len(x) > 1]:
        if token in t:
            score += 1.0
    if any("\u4e00" <= c <= "\u9fff" for c in q):
        grams = [q[i : i + 2] for i in range(max(0, len(q) - 1))]
        score += sum(0.5 for g in grams if g and g in t)
    return score


def keyword_chunk_hits(db: Session, query: str, limit: int = 20) -> list[EvidenceHit]:
    papers = list(
        db.scalars(select(Paper).where(Paper.status == "indexed", Paper.is_public.is_(True))).all()
    )
    hits: list[EvidenceHit] = []
    for paper in papers:
        chunks = list(
            db.scalars(
                select(KnowledgeChunk)
                .where(KnowledgeChunk.paper_id == paper.id)
                .order_by(KnowledgeChunk.chunk_index.asc())
                .limit(40)
            ).all()
        )
        meta_score = score_text(
            query,
            " ".join([paper.title or "", " ".join(paper.authors or []), paper.abstract or ""]),
        )
        best_for_paper: EvidenceHit | None = None
        for ch in chunks:
            s = score_text(query, ch.content)
            if meta_score > s:
                s = meta_score
            if s <= 0:
                continue
            hit = EvidenceHit(
                chunk_id=ch.id,
                paper_id=paper.id,
                title=paper.title,
                authors=list(paper.authors or []),
                year=paper.publication_year,
                content=ch.content,
                page_start=ch.page_start,
                page_end=ch.page_end,
                score=s,
                source_channel="keyword",
            )
            if best_for_paper is None or hit.score > best_for_paper.score:
                best_for_paper = hit
        if best_for_paper:
            hits.append(best_for_paper)
    hits.sort(key=lambda x: x.score, reverse=True)
    return hits[:limit]


def _vector_hits_pgvector(
    db: Session, query_vec: list[float], model_id: str, limit: int
) -> list[EvidenceHit]:
    # cosine distance: <=> ；相似度约为 1 - distance（归一化向量时）
    sql = text(
        """
        SELECT e.chunk_id, e.paper_id, e.vector <=> :qvec AS dist
        FROM chunk_embeddings e
        WHERE e.model_id = :model_id
        ORDER BY e.vector <=> :qvec
        LIMIT :limit
        """
    )
    # pgvector 接受 '[1,2,...]' 字面量
    qvec = "[" + ",".join(str(float(x)) for x in query_vec) + "]"
    rows = db.execute(sql, {"qvec": qvec, "model_id": model_id, "limit": limit}).mappings().all()
    hits: list[EvidenceHit] = []
    for r in rows:
        chunk = db.get(KnowledgeChunk, r["chunk_id"])
        paper = db.get(Paper, r["paper_id"])
        if not chunk or not paper or paper.status != "indexed" or not paper.is_public:
            continue
        dist = float(r["dist"])
        sim = max(0.0, 1.0 - dist)
        if sim <= 0.15:
            continue
        hits.append(
            EvidenceHit(
                chunk_id=chunk.id,
                paper_id=paper.id,
                title=paper.title,
                authors=list(paper.authors or []),
                year=paper.publication_year,
                content=chunk.content,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                score=sim * 10.0,
                source_channel="vector",
            )
        )
    return hits


def _vector_hits_python(
    db: Session, query_vec: list[float], model_id: str, limit: int
) -> list[EvidenceHit]:
    rows = list(db.scalars(select(ChunkEmbedding).where(ChunkEmbedding.model_id == model_id)).all())
    scored: list[tuple[float, ChunkEmbedding]] = []
    for emb in rows:
        s = cosine_similarity(query_vec, emb.vector)
        if s > 0.15:
            scored.append((s, emb))
    scored.sort(key=lambda x: x[0], reverse=True)
    hits: list[EvidenceHit] = []
    for s, emb in scored[:limit]:
        chunk = db.get(KnowledgeChunk, emb.chunk_id)
        paper = db.get(Paper, emb.paper_id)
        if not chunk or not paper or paper.status != "indexed" or not paper.is_public:
            continue
        hits.append(
            EvidenceHit(
                chunk_id=chunk.id,
                paper_id=paper.id,
                title=paper.title,
                authors=list(paper.authors or []),
                year=paper.publication_year,
                content=chunk.content,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                score=float(s) * 10.0,
                source_channel="vector",
            )
        )
    return hits


def vector_chunk_hits(
    db: Session,
    query_vec: list[float],
    model_id: str,
    limit: int = 20,
) -> list[EvidenceHit]:
    if DATABASE_URL.startswith("postgresql"):
        try:
            return _vector_hits_pgvector(db, query_vec, model_id, limit)
        except Exception:
            # 扩展未就绪时回退
            return _vector_hits_python(db, query_vec, model_id, limit)
    return _vector_hits_python(db, query_vec, model_id, limit)


def merge_hits(keyword: list[EvidenceHit], vector: list[EvidenceHit], limit: int = 20) -> list[EvidenceHit]:
    kw_ids = {h.chunk_id for h in keyword}
    vec_ids = {h.chunk_id for h in vector}
    by_chunk: dict[str, EvidenceHit] = {}
    for h in keyword + vector:
        prev = by_chunk.get(h.chunk_id)
        if not prev:
            channel = "hybrid" if h.chunk_id in kw_ids and h.chunk_id in vec_ids else h.source_channel
            by_chunk[h.chunk_id] = EvidenceHit(
                chunk_id=h.chunk_id,
                paper_id=h.paper_id,
                title=h.title,
                authors=h.authors,
                year=h.year,
                content=h.content,
                page_start=h.page_start,
                page_end=h.page_end,
                score=h.score,
                source_channel=channel,
            )
            continue
        prev.score = prev.score + h.score
        prev.source_channel = "hybrid"
    return sorted(by_chunk.values(), key=lambda x: x.score, reverse=True)[:limit]


def hybrid_retrieve(
    db: Session,
    query: str,
    *,
    top_k: int = 8,
    embedding: EmbeddingAdapter | None = None,
    reranker: RerankerAdapter | None = None,
    require_rerank: bool = True,
) -> tuple[list[EvidenceHit], dict]:
    top_k = max(1, min(top_k, 20))
    emb = embedding or get_embedding_adapter()
    rr = reranker or get_reranker_adapter()

    kw = keyword_chunk_hits(db, query, limit=20)
    query_vec = emb.embed([query])[0]
    model_id = emb.model_id
    vec = vector_chunk_hits(db, query_vec, model_id=model_id, limit=20)
    if not vec:
        raise RuntimeError(
            f"公用知识库没有模型 {model_id} 的切片向量，请先运行 scripts/embed_corpus.py 重建索引"
        )

    merged = merge_hits(kw, vec, limit=20)
    if not merged:
        return [], {"model_id": model_id, "keyword": len(kw), "vector": len(vec), "after_merge": 0}

    if require_rerank:
        ranked = rr.rerank(query, [m.content for m in merged], top_k=min(top_k * 2, 20))
        ordered = []
        for i, score in ranked:
            if 0 <= i < len(merged):
                h = merged[i]
                h.score = float(score)
                ordered.append(h)
        ordered = ordered[:top_k]
    else:
        ordered = merged[:top_k]

    meta = {
        "model_id": model_id,
        "reranker_model_id": rr.model_id,
        "keyword": len(kw),
        "vector": len(vec),
        "after_merge": len(merged),
        "after_rerank": len(ordered),
        "vector_backend": "pgvector" if DATABASE_URL.startswith("postgresql") else "python",
    }
    return ordered, meta


def evidence_to_paper_hits(evidence: list[EvidenceHit], top_k: int = 8) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for h in evidence:
        if h.paper_id in seen:
            continue
        seen.add(h.paper_id)
        out.append(
            {
                "paper_id": h.paper_id,
                "title": h.title,
                "authors": h.authors,
                "year": h.year,
                "source": "public_kb",
                "snippet": h.content[:240],
                "page_start": h.page_start,
                "page_end": h.page_end,
                "score": h.score,
            }
        )
        if len(out) >= top_k:
            break
    return out
