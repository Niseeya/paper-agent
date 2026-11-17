#!/usr/bin/env python3
"""为已入库切片生成 Embedding（默认本地 BAAI/bge-m3）。

用法：
  conda activate paperAgent
  export DATABASE_URL=postgresql+psycopg://paper_agent@localhost:5433/paper_agent
  export EMBEDDING_BACKEND=local
  export HF_ENDPOINT=https://hf-mirror.com   # 国内可加速拉取模型
  python scripts/embed_corpus.py
  python scripts/embed_corpus.py --limit 20  # 试跑
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from backend.app.adapters.embedding import get_embedding_adapter  # noqa: E402
from backend.app.db import SessionLocal, init_db  # noqa: E402
from backend.app.models import KnowledgeChunk  # noqa: E402
from backend.app.models.embedding import ChunkEmbedding  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="为知识库切片生成向量")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0, help="仅处理前 N 条未嵌入切片，0=全部")
    parser.add_argument("--force", action="store_true", help="覆盖同模型已有向量")
    args = parser.parse_args()

    init_db()
    adapter = get_embedding_adapter()
    model_id = adapter.model_id
    print(f"model_id={model_id}")

    db = SessionLocal()
    try:
        chunks = list(db.scalars(select(KnowledgeChunk).order_by(KnowledgeChunk.paper_id, KnowledgeChunk.chunk_index)).all())
        if not args.force:
            existing = {
                e.chunk_id
                for e in db.scalars(select(ChunkEmbedding).where(ChunkEmbedding.model_id == model_id)).all()
            }
            chunks = [c for c in chunks if c.id not in existing]
        if args.limit > 0:
            chunks = chunks[: args.limit]
        if not chunks:
            print("无需嵌入：没有待处理切片")
            return 0

        print(f"待嵌入切片: {len(chunks)}")
        done = 0
        for i in range(0, len(chunks), args.batch_size):
            batch = chunks[i : i + args.batch_size]
            vectors = adapter.embed([c.content for c in batch])
            if len(vectors) != len(batch):
                raise RuntimeError("向量条数与切片不一致")
            for ch, vec in zip(batch, vectors):
                if args.force:
                    old = db.scalars(
                        select(ChunkEmbedding).where(
                            ChunkEmbedding.chunk_id == ch.id,
                            ChunkEmbedding.model_id == model_id,
                        )
                    ).first()
                    if old:
                        db.delete(old)
                        db.flush()
                db.add(
                    ChunkEmbedding(
                        id=uuid.uuid5(uuid.NAMESPACE_URL, f"{ch.id}:{model_id}").hex,
                        chunk_id=ch.id,
                        paper_id=ch.paper_id,
                        model_id=model_id,
                        dims=len(vec),
                        vector=vec,
                    )
                )
            db.commit()
            done += len(batch)
            print(f"  embedded {done}/{len(chunks)}")
        print(f"完成: model_id={model_id} count={done}")
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"[错误] {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
