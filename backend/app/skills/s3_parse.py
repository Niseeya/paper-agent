"""S3 论文解析 Skill：文本型 PDF -> 正文、章节树、切片。"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from backend.app.services.pdf_parser import chunk_pages, parse_pdf, sha256_file
from backend.app.skills.base import SkillRequest, SkillResult


class S3Input(BaseModel):
    pdf_path: str
    source_type: str = "user_upload"
    file_name: str | None = None


class SectionNode(BaseModel):
    title: str
    page_start: int
    page_end: int | None = None


class ChunkOut(BaseModel):
    chunk_index: int
    page_start: int
    page_end: int
    content: str


class S3Output(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    abstract: str = ""
    page_count: int
    section_tree: list[SectionNode] = Field(default_factory=list)
    section_recognized: bool
    chunks: list[ChunkOut]
    sha256: str


def _to_output(pdf_path: Path) -> S3Output:
    parsed = parse_pdf(pdf_path)
    chunks = chunk_pages(parsed.pages)
    return S3Output(
        title=parsed.title,
        authors=parsed.authors,
        year=parsed.year,
        abstract=parsed.abstract,
        page_count=parsed.page_count,
        section_tree=[
            SectionNode(
                title=s.title,
                page_start=s.page_start,
                page_end=s.page_end,
            )
            for s in parsed.section_tree
        ],
        section_recognized=parsed.section_recognized,
        chunks=[ChunkOut.model_validate(c) for c in chunks],
        sha256=sha256_file(pdf_path),
    )


def run_s3(req: SkillRequest | dict[str, Any]) -> SkillResult:
    started = time.perf_counter()
    if isinstance(req, dict):
        req = SkillRequest(skill_code="S3", input=req)
    try:
        payload = S3Input.model_validate(req.input)
    except ValidationError as exc:
        return SkillResult(
            skill_code="S3",
            status="failed",
            error=f"输入校验失败: {exc}",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    path = Path(payload.pdf_path)
    if not path.exists():
        return SkillResult(
            skill_code="S3",
            status="failed",
            error=f"PDF 不存在: {path}",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    try:
        data = _to_output(path)
        # 验收：文本型样例必须识别出章节；若未识别则标记警告，不伪造章节
        warnings: list[str] = []
        if not data.section_recognized:
            warnings.append("章节未识别，已按页切分")
        if not data.chunks:
            return SkillResult(
                skill_code="S3",
                status="failed",
                error="未提取到文本，可能是扫描件或加密 PDF",
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        return SkillResult(
            skill_code="S3",
            status="succeeded",
            data=data.model_dump(),
            warnings=warnings,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        return SkillResult(
            skill_code="S3",
            status="failed",
            error=str(exc),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
