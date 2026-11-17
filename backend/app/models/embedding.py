"""切片向量。Postgres 使用 pgvector；SQLite 回退 JSON（仅开发兜底）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from backend.app.db import DATABASE_URL, Base

if DATABASE_URL.startswith("postgresql"):
    from pgvector.sqlalchemy import Vector

    _VectorType = Vector(1024)
else:
    _VectorType = JSON


class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"
    __table_args__ = (UniqueConstraint("chunk_id", "model_id", name="uq_chunk_model"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chunk_id: Mapped[str] = mapped_column(String(64), ForeignKey("knowledge_chunks.id"), nullable=False)
    paper_id: Mapped[str] = mapped_column(String(64), ForeignKey("papers.id"), nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    dims: Mapped[int] = mapped_column(Integer, nullable=False)
    vector: Mapped[list] = mapped_column(_VectorType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
