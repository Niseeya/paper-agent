"""润色独立测试：对照可确认；不改数字与引用；降重请求被拒绝。"""

from backend.app.skills.polish import run_polish


def test_polish_keeps_numbers_and_citations():
    text = "研究显示增长 12.5%，参见[C1]。因此本文认为该路径有效。"
    result = run_polish({"text": text, "level": "academic"})
    assert result.status == "succeeded"
    data = result.data
    assert data["confirmed"] is False
    assert "12.5%" in data["polished"]
    assert "[C1]" in data["polished"]
    assert data["rejected"] is False


def test_polish_rejects_paraphrase_for_similarity():
    result = run_polish(
        {
            "text": "原段落保持不变。",
            "user_request": "请帮我降重规避查重",
            "level": "deep",
        }
    )
    assert result.status == "succeeded"
    data = result.data
    assert data["rejected"] is True
    assert data["polished"] == "原段落保持不变。"
