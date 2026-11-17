"""S9 独立测试：引用问题含 L1/L2 失败句；逻辑问题含重复与缺论据判断。"""

from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import KnowledgeChunk, Paper
from backend.app.skills.s9_check import run_s9


def test_s9_flags_bad_citation_and_logic():
    db = SessionLocal()
    try:
        paper = db.scalars(select(Paper).where(Paper.status == "indexed").limit(1)).first()
        assert paper
        chunk = db.scalars(
            select(KnowledgeChunk).where(KnowledgeChunk.paper_id == paper.id).limit(1)
        ).first()
        assert chunk
        good_sentence = f"研究表明：{chunk.content[:40]}"
        bad_sentence = "张三（2099）提出了库外观点。"
        dup = "这一结论显而易见。"
        result = run_s9(
            {
                "paragraphs": [
                    good_sentence,
                    bad_sentence,
                    "因此必然如此。",
                    dup,
                    dup,
                ],
                "citations": [
                    {
                        "sentence": good_sentence,
                        "paper_id": paper.id,
                        "title": paper.title,
                        "authors": list(paper.authors or []),
                        "year": paper.publication_year,
                        "page_start": chunk.page_start,
                        "evidence_snippet": chunk.content[:80],
                        "is_formal": True,
                    },
                    {
                        "sentence": bad_sentence,
                        "paper_id": "fake-outside",
                        "title": "库外题名",
                        "authors": ["张三"],
                        "year": 2099,
                        "page_start": 1,
                        "evidence_snippet": "无",
                        "is_formal": True,
                    },
                ],
            }
        )
    finally:
        db.close()

    assert result.status == "succeeded", result.error
    data = result.data
    assert any("L1" in i["detail"] or "L2" in i["detail"] for i in data["citation_issues"])
    assert any(i["detail"] == "明显重复" for i in data["logic_issues"])
    assert data["passed"] is False
