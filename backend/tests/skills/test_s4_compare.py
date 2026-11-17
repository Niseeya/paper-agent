"""S4 独立测试：2～8 篇已索引论文 -> 带证据对比；空缺填库内未找到。"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def paper_ids():
    from backend.app.db import SessionLocal, init_db
    from backend.app.models import Paper
    from scripts.import_corpus_to_db import main as import_main

    if not (ROOT / "data" / "storage" / "papers").exists():
        pytest.skip("无 corpus")
    init_db()
    import_main()
    db = SessionLocal()
    try:
        ids = list(
            db.scalars(select(Paper.id).where(Paper.status == "indexed").limit(3)).all()
        )
        if len(ids) < 2:
            pytest.skip("已索引论文不足 2 篇")
        return ids
    finally:
        db.close()


def test_s4_compare_matrix(paper_ids):
    from backend.app.skills.s4_compare import MISSING, run_s4

    result = run_s4({"paper_ids": paper_ids[:3]})
    assert result.status == "succeeded", result.error
    data = result.data
    assert len(data["papers"]) == len(paper_ids[:3])
    assert len(data["matrix"]) >= 1
    for row in data["matrix"]:
        assert row["dimension"]
        assert len(row["cells"]) == len(paper_ids[:3])
        for cell in row["cells"]:
            assert cell["value"]
            assert cell["paper_id"]


def test_s4_missing_paper_marked(paper_ids):
    from backend.app.skills.s4_compare import MISSING, run_s4

    ids = [paper_ids[0], "not-exist-paper-id"]
    result = run_s4({"paper_ids": ids})
    assert result.status == "succeeded", result.error
    missing_cells = [
        c
        for row in result.data["matrix"]
        for c in row["cells"]
        if c["paper_id"] == "not-exist-paper-id"
    ]
    assert missing_cells
    assert all(c["value"] == MISSING for c in missing_cells)
