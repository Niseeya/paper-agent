"""公用知识库核心表。字段对齐数据库设计说明书，SQLite/Postgres 共用。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.app.db import Base


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[list] = mapped_column(JSON, default=list)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="preset")
    uploader_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_preset: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="indexed")
    section_recognized: Mapped[bool] = mapped_column(Boolean, default=False)
    section_tree: Mapped[list] = mapped_column(JSON, default=list)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    offlined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    files: Mapped[list["DocumentFile"]] = relationship(back_populates="paper")
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="paper")


class DocumentFile(Base):
    __tablename__ = "document_files"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    paper_id: Mapped[str] = mapped_column(String(64), ForeignKey("papers.id"), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rights_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)
    parse_status: Mapped[str] = mapped_column(String(30), default="parsed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    paper: Mapped[Paper] = relationship(back_populates="files")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (UniqueConstraint("document_file_id", "chunk_index", name="uq_chunk_doc_index"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    paper_id: Mapped[str] = mapped_column(String(64), ForeignKey("papers.id"), nullable=False)
    document_file_id: Mapped[str] = mapped_column(String(64), ForeignKey("document_files.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    paper: Mapped[Paper] = relationship(back_populates="chunks")
