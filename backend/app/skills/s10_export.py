"""S10 文档导出：生成可打开的 DOCX 与 PDF。"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from backend.app.skills.base import SkillRequest, SkillResult

ROOT = Path(__file__).resolve().parents[3]
EXPORT_DIR = ROOT / "data" / "exports"


class SectionIn(BaseModel):
    title: str
    paragraphs: list[str] = Field(default_factory=list)


class ReferenceIn(BaseModel):
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    paper_id: str = ""


class S10Input(BaseModel):
    title: str
    author: str = "作者"
    sections: list[SectionIn] = Field(min_length=1)
    references: list[ReferenceIn] = Field(default_factory=list)
    mode: str = "draft"  # draft | final
    citation_check_passed: bool = False
    output_dir: str | None = None


class S10Output(BaseModel):
    mode: str
    docx_path: str
    pdf_path: str
    markdown_path: str


def _format_ref(i: int, ref: ReferenceIn) -> str:
    authors = "，".join(ref.authors) if ref.authors else "作者未识别"
    year = str(ref.year) if ref.year else "年份未识别"
    title = ref.title or "题名未识别"
    return f"[{i}] {authors}. {title}. {year}."


def _render_markdown(
    title: str, author: str, sections: list[SectionIn], mode: str, references: list[ReferenceIn]
) -> str:
    lines = [f"# {title}", "", f"作者：{author}", ""]
    if mode == "draft":
        lines.extend(["> 辅助生成草稿", ""])
    for sec in sections:
        lines.append(f"## {sec.title}")
        lines.append("")
        for p in sec.paragraphs:
            lines.append(p)
            lines.append("")
    if references:
        lines.extend(["## 参考文献", ""])
        for i, ref in enumerate(references, start=1):
            lines.append(_format_ref(i, ref))
            lines.append("")
    return "\n".join(lines)


def _write_docx(
    path: Path,
    title: str,
    author: str,
    sections: list[SectionIn],
    mode: str,
    references: list[ReferenceIn],
) -> None:
    from docx import Document

    doc = Document()
    doc.add_heading(title, level=0)
    doc.add_paragraph(f"作者：{author}")
    if mode == "draft":
        doc.add_paragraph("辅助生成草稿")
    for sec in sections:
        doc.add_heading(sec.title, level=1)
        for p in sec.paragraphs:
            doc.add_paragraph(p)
    if references:
        doc.add_heading("参考文献", level=1)
        for i, ref in enumerate(references, start=1):
            doc.add_paragraph(_format_ref(i, ref))
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)


def _write_pdf(
    path: Path,
    title: str,
    author: str,
    sections: list[SectionIn],
    mode: str,
    references: list[ReferenceIn] | None = None,
) -> None:
    """无 Pandoc 时用 reportlab 生成最小可用 PDF；失败则不写空文件。"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise RuntimeError("缺少 reportlab，无法生成 PDF") from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    y = height - 72
    c.setFont("STSong-Light", 16)
    c.drawString(72, y, title[:40])
    y -= 28
    c.setFont("STSong-Light", 11)
    c.drawString(72, y, f"作者：{author}")
    y -= 20
    if mode == "draft":
        c.drawString(72, y, "辅助生成草稿")
        y -= 24
    for sec in sections:
        if y < 72:
            c.showPage()
            c.setFont("STSong-Light", 11)
            y = height - 72
        c.setFont("STSong-Light", 13)
        c.drawString(72, y, sec.title[:40])
        y -= 20
        c.setFont("STSong-Light", 11)
        for p in sec.paragraphs:
            for i in range(0, len(p), 32):
                if y < 72:
                    c.showPage()
                    c.setFont("STSong-Light", 11)
                    y = height - 72
                c.drawString(72, y, p[i : i + 32])
                y -= 16
            y -= 8
    if references:
        if y < 100:
            c.showPage()
            y = height - 72
        c.setFont("STSong-Light", 13)
        c.drawString(72, y, "参考文献")
        y -= 20
        c.setFont("STSong-Light", 11)
        for i, ref in enumerate(references, start=1):
            text = _format_ref(i, ref)
            for j in range(0, len(text), 32):
                if y < 72:
                    c.showPage()
                    c.setFont("STSong-Light", 11)
                    y = height - 72
                c.drawString(72, y, text[j : j + 32])
                y -= 16
            y -= 6
    c.save()
    if not path.exists() or path.stat().st_size == 0:
        path.unlink(missing_ok=True)
        raise RuntimeError("PDF 生成结果为空")


def run_s10(req: SkillRequest | dict[str, Any]) -> SkillResult:
    started = time.perf_counter()
    if isinstance(req, dict):
        req = SkillRequest(skill_code="S10", input=req)
    try:
        payload = S10Input.model_validate(req.input)
    except ValidationError as exc:
        return SkillResult(
            skill_code="S10",
            status="failed",
            error=f"输入校验失败: {exc}",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    if payload.mode == "final" and not payload.citation_check_passed:
        return SkillResult(
            skill_code="S10",
            status="failed",
            error="定稿导出被拒绝：引用核查未全部通过；可改为草稿导出",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    out_dir = Path(payload.output_dir) if payload.output_dir else EXPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"export_{int(time.time())}"
    md_path = out_dir / f"{stem}.md"
    docx_path = out_dir / f"{stem}.docx"
    pdf_path = out_dir / f"{stem}.pdf"

    try:
        md_path.write_text(
            _render_markdown(
                payload.title, payload.author, payload.sections, payload.mode, payload.references
            ),
            encoding="utf-8",
        )
        _write_docx(
            docx_path,
            payload.title,
            payload.author,
            payload.sections,
            payload.mode,
            payload.references,
        )
        _write_pdf(
            pdf_path,
            payload.title,
            payload.author,
            payload.sections,
            payload.mode,
            payload.references,
        )
        # 验收：DOCX 可读正文；PDF 以 %PDF 开头且非空
        from docx import Document

        doc = Document(docx_path)
        text = "\n".join(p.text for p in doc.paragraphs)
        assert payload.title in text or any(payload.title[:6] in p for p in text.splitlines())
        raw = pdf_path.read_bytes()
        assert raw.startswith(b"%PDF") and len(raw) > 100
        out = S10Output(
            mode=payload.mode,
            docx_path=str(docx_path),
            pdf_path=str(pdf_path),
            markdown_path=str(md_path),
        )
        return SkillResult(
            skill_code="S10",
            status="succeeded",
            data=out.model_dump(),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        for p in (docx_path, pdf_path):
            if p.exists() and p.stat().st_size == 0:
                p.unlink(missing_ok=True)
        return SkillResult(
            skill_code="S10",
            status="failed",
            error=str(exc),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
