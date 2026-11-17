"""S8 独立测试：大纲已确认后生成正文；正式引用回链库内。"""

from backend.app.skills.s8_write import run_s8


def test_s8_requires_outline_confirm():
    result = run_s8({"section_title": "文献综述", "outline_confirmed": False})
    assert result.status == "failed"
    assert "大纲未确认" in (result.error or "")


def test_s8_writes_with_real_citations():
    result = run_s8(
        {
            "section_title": "国产青春电影的怀旧叙事",
            "writing_intent": "梳理怀旧叙事表现",
            "outline_confirmed": True,
            "research_goal": "青春电影怀旧",
        }
    )
    assert result.status == "succeeded", result.error
    citations = result.data["citations"]
    assert len(citations) >= 1
    for c in citations:
        assert c["paper_id"]
        assert c["title"]
        assert c["page_start"] >= 1
        assert c["snippet"]
    paragraphs = result.data["paragraphs"]
    assert len(paragraphs) >= 3  # 提出问题 → 分述 → 小结
    full = "\n".join(p["text"] for p in paragraphs)
    assert "围绕" in paragraphs[0]["text"]
    assert "综合以上" in paragraphs[-1]["text"]
    # 正式引用标记能回链到 citations
    cite_ids = {c["citation_id"] for c in citations}
    found = set()
    import re

    for mid in re.findall(r"\[(C\d+)\]", full):
        assert mid in cite_ids
        found.add(mid)
    assert found