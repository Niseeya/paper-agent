"""S2 独立测试：中英文关键词检索，结果必须来自公用知识库。"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def imported_kb():
    storage = ROOT / "data" / "storage" / "papers"
    if not storage.exists() or not any(storage.iterdir()):
        pytest.skip("无 corpus 解析产物，先运行 scripts/sync_corpus.py")

    from backend.app.db import SessionLocal, init_db
    from backend.app.models import Paper
    from scripts.import_corpus_to_db import main as import_main

    init_db()
    rc = import_main()
    assert rc == 0, "corpus 导入失败"

    db = SessionLocal()
    try:
        count = db.query(Paper).filter(Paper.status == "indexed").count()
        if count == 0:
            pytest.skip("无已索引论文")
    finally:
        db.close()


def test_s2_chinese_keywords(imported_kb):
    from backend.app.skills.s2_retrieve import run_s2

    # 独立测试覆盖关键词路径；混合检索另测
    result = run_s2({"query": "电视剧 视像 文化", "language": "zh", "top_k": 5, "mode": "keyword"})
    assert result.status == "succeeded", result.error
    papers = result.data["papers"]
    assert len(papers) >= 1
    for p in papers:
        assert p["paper_id"]
        assert p["title"]
        assert isinstance(p["authors"], list)
        assert "year" in p
        assert p["source"] == "public_kb"
        # 命中必须带回页码证据，便于回链
        assert p.get("page_start") is not None and p["page_start"] >= 1


def test_s2_english_keywords(imported_kb):
    from backend.app.skills.s2_retrieve import run_s2

    result = run_s2(
        {"query": "film television aesthetic", "language": "en", "top_k": 5, "mode": "keyword"}
    )
    assert result.status == "succeeded", result.error
    for p in result.data["papers"]:
        assert p["paper_id"]
        assert p["title"]
        assert p["source"] == "public_kb"


def test_s2_hybrid_requires_vectors_or_succeeds(imported_kb):
    from sqlalchemy import func, select

    from backend.app.db import SessionLocal
    from backend.app.models.embedding import ChunkEmbedding
    from backend.app.skills.s2_retrieve import run_s2

    db = SessionLocal()
    try:
        n = db.scalar(select(func.count()).select_from(ChunkEmbedding)) or 0
    finally:
        db.close()

    result = run_s2({"query": "青春电影 怀旧", "language": "zh", "top_k": 5, "mode": "hybrid"})
    if n == 0:
        assert result.status == "failed"
        assert "向量" in (result.error or "")
    else:
        assert result.status == "succeeded", result.error
        assert result.data["papers"]
        assert result.data["retrieval_meta"].get("model_id")

