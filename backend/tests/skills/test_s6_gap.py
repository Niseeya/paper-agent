"""S6 独立测试：输出候选空白，类型为建议，有证据或标明证据不足。"""

from backend.app.skills.s6_gap import EVIDENCE_LACK, run_s6


def test_s6_gaps_are_suggestions():
    result = run_s6(
        {
            "research_status": "现有研究对青春电影产业机制探讨较多，但对跨媒介改编的实证研究尚显不足。",
            "paper_ids": [],
        }
    )
    assert result.status == "succeeded", result.error
    gaps = result.data["gaps"]
    assert len(gaps) >= 1
    for g in gaps:
        assert g["type"] == "建议"
        assert g["evidence_status"] in ("有证据", EVIDENCE_LACK)
        if g["evidence_status"] == "有证据":
            assert len(g["evidence_refs"]) >= 1
