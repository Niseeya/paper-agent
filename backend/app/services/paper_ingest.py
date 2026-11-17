"""用户上传 PDF：解析 → 切片 → 入库 →（可选）向量化。"""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.adapters.embedding import EmbeddingAdapter, get_embedding_adapter
from backend.app.models import DocumentFile, KnowledgeChunk, Paper
from backend.app.models.embedding import ChunkEmbedding
from backend.app.services.pdf_parser import chunk_pages, parse_pdf, sha256_file, title_from_filename

ROOT = Path(__file__).resolve().parents[3]
STORAGE = Path(__import__("os").getenv("DATA_DIR", ROOT / "data")) / "storage" / "papers"
MAX_MB = 30


class IngestError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _paper_id_from_sha(digest: str) -> str:
    return digest[:32]


def ingest_pdf(
    db: Session,
    *,
    src_path: Path,
    file_name: str,
    uploader_id: str,
    rights_confirmed: bool,
    embed: bool = True,
    embedding: EmbeddingAdapter | None = None,
) -> dict:
    if not rights_confirmed:
        raise IngestError("PAPER_RIGHTS_REQUIRED", "未勾选上传授权，不接收文件")
    if src_path.suffix.lower() != ".pdf":
        raise IngestError("PAPER_FILE_INVALID", "只接受 PDF")
    size = src_path.stat().st_size
    if size <= 0 or size > MAX_MB * 1024 * 1024:
        raise IngestError("PAPER_FILE_INVALID", f"文件大小须在 1B～{MAX_MB}MB")

    digest = sha256_file(src_path)
    existing = db.scalar(select(DocumentFile).where(DocumentFile.sha256 == digest))
    if existing:
        raise IngestError("PAPER_DUPLICATE", f"公用库已有相同文件：{existing.paper_id}")

    try:
        parsed = parse_pdf(src_path)
    except Exception as exc:  # noqa: BLE001
        raise IngestError("PAPER_PARSE_FAILED", f"解析失败: {exc}") from exc
    if not parsed.full_text.strip():
        raise IngestError("PAPER_PARSE_FAILED", "未提取到文本，可能是扫描件或加密 PDF")

    chunks = chunk_pages(parsed.pages)
    paper_id = _paper_id_from_sha(digest)
    file_title = title_from_filename(file_name)
    parsed_title = (parsed.title or "").strip()
    # 文件名题名通常更可靠；PDF 元数据常是作者行/卷期噪音
    noisy_meta = (
        not parsed_title
        or parsed_title == "未识别题名"
        or len(parsed_title) < 8
        or parsed_title.lower().startswith("volume ")
        or "*" in parsed_title
        or parsed_title.count(",") >= 2 and len(parsed_title) < 40
    )
    if file_title and len(file_title) >= 8 and (noisy_meta or len(file_title) >= len(parsed_title)):
        title = file_title[:200]
    else:
        title = parsed_title[:200] if parsed_title else (file_title or "未识别题名")

    STORAGE.mkdir(parents=True, exist_ok=True)
    paper_dir = STORAGE / paper_id
    paper_dir.mkdir(parents=True, exist_ok=True)
    stored = paper_dir / "source.pdf"
    shutil.copy2(src_path, stored)
    (paper_dir / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {
        "paper_id": paper_id,
        "sha256": digest,
        "file_name": file_name,
        "title": title,
        "authors": parsed.authors,
        "year": parsed.year,
        "page_count": parsed.page_count,
        "section_recognized": parsed.section_recognized,
        "status": "indexed",
    }
    (paper_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    now = datetime.now(timezone.utc)
    paper = Paper(
        id=paper_id,
        title=title,
        authors=parsed.authors or [],
        publication_year=parsed.year,
        abstract=parsed.abstract or "",
        source_type="user_upload",
        uploader_id=uploader_id,
        is_preset=False,
        is_public=True,
        status="indexed",
        section_recognized=parsed.section_recognized,
        section_tree=[
            {"title": n.title, "page_start": n.page_start, "page_end": n.page_end}
            for n in parsed.section_tree
        ],
        page_count=parsed.page_count,
        indexed_at=now,
        created_at=now,
    )
    doc = DocumentFile(
        id=paper_id,
        paper_id=paper_id,
        storage_key=f"papers/{paper_id}/source.pdf",
        file_name=file_name,
        source_path=None,
        file_size=size,
        sha256=digest,
        page_count=parsed.page_count,
        rights_confirmed=True,
        parse_status="parsed",
        created_at=now,
    )
    db.add(paper)
    db.add(doc)
    chunk_rows: list[KnowledgeChunk] = []
    for ch in chunks:
        row = KnowledgeChunk(
            id=uuid.uuid5(uuid.NAMESPACE_URL, f"{paper_id}:{ch['chunk_index']}").hex,
            paper_id=paper_id,
            document_file_id=paper_id,
            chunk_index=int(ch["chunk_index"]),
            page_start=int(ch["page_start"]),
            page_end=int(ch["page_end"]),
            content=ch["content"],
            created_at=now,
        )
        db.add(row)
        chunk_rows.append(row)
    db.flush()

    embedded = 0
    model_id = None
    if embed:
        adapter = embedding or get_embedding_adapter()
        model_id = adapter.model_id
        vectors = adapter.embed([c.content for c in chunk_rows])
        for row, vec in zip(chunk_rows, vectors):
            db.add(
                ChunkEmbedding(
                    id=uuid.uuid5(uuid.NAMESPACE_URL, f"{row.id}:{model_id}").hex,
                    chunk_id=row.id,
                    paper_id=paper_id,
                    model_id=model_id,
                    dims=len(vec),
                    vector=vec,
                    created_at=now,
                )
            )
            embedded += 1
    db.commit()
    return {
        "id": paper_id,
        "title": title,
        "authors": parsed.authors,
        "year": parsed.year,
        "page_count": parsed.page_count,
        "section_recognized": parsed.section_recognized,
        "chunk_count": len(chunk_rows),
        "embedded": embedded,
        "embedding_model_id": model_id,
        "status": "indexed",
    }
