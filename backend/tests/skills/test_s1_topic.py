"""S1 独立测试：一段研究主题 -> 合法结构，非自由散文。"""

from backend.app.skills.s1_topic import run_s1


def test_s1_returns_structured_fields():
    result = run_s1(
        {
            "topic_text": "新世纪国产青春电影中的怀旧叙事与青年形象建构研究",
        }
    )
    assert result.status == "succeeded", result.error
    data = result.data
    assert data["topic_name"]
    assert data["research_object"]
    assert isinstance(data["keywords"], list) and len(data["keywords"]) >= 2
    assert data["problem_boundary"]
    # 不应只是原文整段复述为唯一字段
    assert set(data.keys()) >= {"topic_name", "research_object", "keywords", "problem_boundary"}


def test_s1_rejects_too_short():
    result = run_s1({"topic_text": "电影"})
    assert result.status == "failed"
