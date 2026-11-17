"""S5 独立测试：一组已索引论文 -> 方向分类，每类有依据论文。"""

from backend.app.skills.s5_classify import run_s5


def test_s5_classifies_public_kb():
    result = run_s5({})
    assert result.status == "succeeded", result.error
    dirs = result.data["directions"]
    assert len(dirs) >= 1
    for d in dirs:
        assert d["direction"]
        assert len(d["paper_ids"]) >= 1
        assert len(d["titles"]) == len(d["paper_ids"])
        assert d["rationale"]
