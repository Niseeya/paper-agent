#!/usr/bin/env python3
"""把 chunk_embeddings.vector 从 JSON 迁到 pgvector vector(1024)，并建 HNSW 索引。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from backend.app.db import engine


def main() -> int:
    url = str(engine.url)
    if not url.startswith("postgresql"):
        print(f"[错误] 需要 Postgres，当前: {url}")
        return 2

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        cols = {
            r[0]
            for r in conn.execute(
                text(
                    """
                    SELECT column_name, data_type, udt_name
                    FROM information_schema.columns
                    WHERE table_name = 'chunk_embeddings'
                    """
                )
            )
        }
        # 探测当前 vector 列类型
        row = conn.execute(
            text(
                """
                SELECT data_type, udt_name
                FROM information_schema.columns
                WHERE table_name='chunk_embeddings' AND column_name='vector'
                """
            )
        ).first()
        if not row:
            print("[错误] 表 chunk_embeddings 无 vector 列")
            return 1
        data_type, udt = row
        print(f"当前 vector 列: data_type={data_type} udt={udt}")

        if udt == "vector":
            print("已是 pgvector，跳过数据迁移")
        else:
            print("添加 embedding 临时列并回填…")
            conn.execute(text("ALTER TABLE chunk_embeddings ADD COLUMN IF NOT EXISTS embedding vector(1024)"))
            # JSON/text -> vector
            updated = conn.execute(
                text(
                    """
                    UPDATE chunk_embeddings
                    SET embedding = (vector::text)::vector
                    WHERE embedding IS NULL AND vector IS NOT NULL
                    """
                )
            )
            print(f"回填行数: {updated.rowcount}")
            conn.execute(text("ALTER TABLE chunk_embeddings DROP COLUMN vector"))
            conn.execute(text("ALTER TABLE chunk_embeddings RENAME COLUMN embedding TO vector"))
            print("已替换为 vector(1024)")

        # 索引
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_chunk_embeddings_vector_hnsw
                ON chunk_embeddings
                USING hnsw (vector vector_cosine_ops)
                """
            )
        )
        n = conn.execute(text("SELECT count(*) FROM chunk_embeddings")).scalar()
        sample = conn.execute(
            text(
                """
                SELECT model_id, dims, vector_dims(vector),
                       (vector <=> (SELECT vector FROM chunk_embeddings LIMIT 1)) AS dist
                FROM chunk_embeddings LIMIT 1
                """
            )
        ).first()
        print(f"完成: rows={n} sample={sample}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
