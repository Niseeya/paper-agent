"""S10 独立测试：生成可打开 DOCX 与 PDF。"""

from pathlib import Path

from docx import Document

from backend.app.skills.s10_export import run_s10

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "exports" / "test_s10"


def test_s10_draft_export_files():
    OUT.mkdir(parents=True, exist_ok=True)
    result = run_s10(
        {
            "title": "测试论文导出",
            "author": "测试作者",
            "mode": "draft",
            "sections": [
                {"title": "绪论", "paragraphs": ["这是正文第一段。", "这是正文第二段。"]},
            ],
            "output_dir": str(OUT),
        }
    )
    assert result.status == "succeeded", result.error
    docx_path = Path(result.data["docx_path"])
    pdf_path = Path(result.data["pdf_path"])
    assert docx_path.exists() and docx_path.stat().st_size > 0
    doc = Document(docx_path)
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "这是正文第一段" in text
    raw = pdf_path.read_bytes()
    assert raw.startswith(b"%PDF") and len(raw) > 100


def test_s10_final_requires_citation_pass():
    result = run_s10(
        {
            "title": "定稿应被拒绝",
            "mode": "final",
            "citation_check_passed": False,
            "sections": [{"title": "一", "paragraphs": ["x"]}],
        }
    )
    assert result.status == "failed"
    assert "定稿" in (result.error or "")
