"""S7 独立测试：研究目标 -> 可编辑大纲，含一至三级标题与写作意图。"""

from backend.app.skills.s7_outline import run_s7


def _collect_levels(nodes, acc=None):
    acc = acc or set()
    for n in nodes:
        acc.add(n["level"])
        assert n["title"] and n["intent"]
        _collect_levels(n.get("children") or [], acc)
    return acc


def test_s7_outline_has_three_levels():
    result = run_s7(
        {
            "research_goal": "梳理新世纪国产青春电影的怀旧叙事与青年形象建构",
            "paper_type": "综述",
        }
    )
    assert result.status == "succeeded", result.error
    data = result.data
    assert data["topic_name"]
    assert data["confirmed"] is False
    levels = _collect_levels(data["nodes"])
    assert {1, 2, 3}.issubset(levels)
