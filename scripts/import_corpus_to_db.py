#!/usr/bin/env python3
"""把 data/storage/papers 与 corpus_state 导入正式数据库。"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def parse_dt(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def main() -> int:
    # 延迟导入，便于测试通过 DATABASE_URL 切换引擎
    from backend.app.db import SessionLocal, init_db  # noqa: E402
    from backend.app.models import DocumentFile, KnowledgeChunk, Paper  # noqa: E402
    from sqlalchemy import delete  # noqa: E402

    storage = ROOT / "data" / "storage" / "papers"
    if not storage.exists():
        print(f"[错误] 未找到解析产物: {storage}")
        return 2

    init_db()
    db = SessionLocal()
    indexed = skipped = failed = 0
    try:
        for paper_dir in sorted(p for p in storage.iterdir() if p.is_dir()):
            meta_path = paper_dir / "meta.json"
            chunks_path = paper_dir / "chunks.json"
            if not meta_path.exists() or not chunks_path.exists():
                failed += 1
                print(f"[failed] 缺少 meta/chunks: {paper_dir.name}")
                continue
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
            paper_id = meta["paper_id"]
            existing = db.get(Paper, paper_id)
            if existing and existing.status == "indexed":
                skipped += 1
                continue

            source_pdf = paper_dir / "source.pdf"
            file_size = source_pdf.stat().st_size if source_pdf.exists() else 0
            if existing:
                paper = existing
            else:
                paper = Paper(id=paper_id)
                db.add(paper)

            paper.title = meta.get("title") or "未识别题名"
            paper.authors = meta.get("authors") or []
            paper.publication_year = meta.get("year")
            paper.abstract = meta.get("abstract") or ""
            paper.source_type = meta.get("source_type") or "preset"
            paper.is_preset = bool(meta.get("is_preset", True))
            paper.is_public = bool(meta.get("is_public", True))
            paper.status = "indexed"
            paper.section_recognized = bool(meta.get("section_recognized"))
            paper.section_tree = meta.get("section_tree") or []
            paper.page_count = meta.get("page_count")
            paper.indexed_at = parse_dt(meta.get("indexed_at"))

            file_id = paper_id
            doc = db.get(DocumentFile, file_id)
            if not doc:
                doc = DocumentFile(id=file_id, paper_id=paper_id, sha256=meta["sha256"])
                db.add(doc)
            doc.storage_key = meta.get("storage_key") or f"papers/{paper_id}/source.pdf"
            doc.file_name = meta.get("file_name") or "source.pdf"
            doc.source_path = meta.get("source_path")
            doc.file_size = file_size
            doc.sha256 = meta["sha256"]
            doc.page_count = meta.get("page_count")
            doc.rights_confirmed = True
            doc.parse_status = "parsed"

            db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.paper_id == paper_id))
            for ch in chunks:
                db.add(
                    KnowledgeChunk(
                        id=uuid.uuid5(uuid.NAMESPACE_URL, f"{paper_id}:{ch['chunk_index']}").hex,
                        paper_id=paper_id,
                        document_file_id=file_id,
                        chunk_index=int(ch["chunk_index"]),
                        page_start=int(ch["page_start"]),
                        page_end=int(ch["page_end"]),
                        content=ch["content"],
                    )
                )
            db.commit()
            indexed += 1
            print(f"[imported] {paper.title}")
    finally:
        db.close()

    print(f"完成: imported={indexed} skipped={skipped} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
