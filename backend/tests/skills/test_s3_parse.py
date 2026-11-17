"""S3 独立测试：带章节的文本型 PDF -> 正文 + 章节树。"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.skills.s3_parse import run_s3

ROOT = Path(__file__).resolve().parents[3]
STORAGE = ROOT / "data" / "storage" / "papers"


def _sample_pdf() -> Path:
    # 优先用已同步入库的 source.pdf；否则用论文目录样例
    if STORAGE.exists():
        for paper_dir in sorted(STORAGE.iterdir()):
            pdf = paper_dir / "source.pdf"
            if pdf.exists():
                return pdf
    papers = ROOT / "论文"
    pdfs = sorted(papers.glob("*.pdf")) if papers.exists() else []
    if not pdfs:
        pytest.skip("无可用 PDF 样例")
    return pdfs[0]


def test_s3_extracts_text_and_sections():
    pdf = _sample_pdf()
    result = run_s3({"pdf_path": str(pdf)})
    assert result.status == "succeeded", result.error
    data = result.data
    assert data["title"]
    assert data["page_count"] >= 1
    assert data["sha256"]
    assert len(data["chunks"]) >= 1
    assert all(c["content"].strip() for c in data["chunks"])
    # 验收：样例必须识别出章节
    assert data["section_recognized"] is True
    assert len(data["section_tree"]) >= 1
    assert all(s["title"] and s["page_start"] for s in data["section_tree"])


def test_s3_rejects_missing_file():
    result = run_s3({"pdf_path": "/tmp/not-exists-paper-agent.pdf"})
    assert result.status == "failed"
    assert result.error
