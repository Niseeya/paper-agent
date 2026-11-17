"""S1 主题结构化：研究主题 -> 主题名称、研究对象、关键词、问题边界。"""

from __future__ import annotations

import re
import time
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from backend.app.skills.base import SkillRequest, SkillResult


class S1Input(BaseModel):
    topic_text: str = Field(min_length=4)


class S1Output(BaseModel):
    topic_name: str
    research_object: str
    keywords: list[str]
    problem_boundary: str


_STOP = {
    "的",
    "与",
    "和",
    "及",
    "对",
    "在",
    "中",
    "研究",
    "分析",
    "探讨",
    "基于",
    "一种",
    "关于",
    "及其",
    "进行",
    "浅析",
    "刍议",
    "试论",
}


def _split_keywords(text: str) -> list[str]:
    # 先按标点切，再抽 2～8 字中文片段与英文词
    parts = re.split(r"[，,、；;。．.\s/|]+", text)
    keywords: list[str] = []
    for p in parts:
        p = p.strip()
        if not p or p in _STOP:
            continue
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9\-_]{1,24}", p):
            keywords.append(p.lower())
            continue
        # 去掉常见动词后缀
        cleaned = re.sub(r"(研究|分析|探讨|探究|考察)$", "", p)
        if 2 <= len(cleaned) <= 12 and cleaned not in _STOP:
            keywords.append(cleaned)
    # 若过少，从整段抽名词性大片段
    if len(keywords) < 3:
        for m in re.finditer(r"[\u4e00-\u9fff]{2,8}", text):
            w = m.group(0)
            if w not in _STOP and w not in keywords:
                keywords.append(w)
            if len(keywords) >= 6:
                break
    # 去重保序
    seen: set[str] = set()
    out: list[str] = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out[:8]


def structure_topic(topic_text: str) -> S1Output:
    text = re.sub(r"\s+", " ", topic_text).strip()
    # 主题名称：取首句或整段截断
    topic_name = re.split(r"[。？！\n]", text)[0].strip()[:40]
    keywords = _split_keywords(text)
    # 研究对象：优先「…中的…」/「对…的」；否则取最长关键词，避免拼接重复
    obj = ""
    m = re.search(
        r"([\u4e00-\u9fffA-Za-z0-9]{2,20})(?:中的|里的)([\u4e00-\u9fffA-Za-z0-9]{2,20})",
        text,
    )
    if m:
        obj = f"{m.group(1)}中的{m.group(2)}"
    else:
        m2 = re.search(r"对([\u4e00-\u9fffA-Za-z0-9]{2,24})的", text)
        if m2:
            obj = m2.group(1)
        elif keywords:
            obj = max(keywords, key=len)
        else:
            obj = topic_name
    obj = obj[:40]
    boundary_bits = []
    if "不" in text or "排除" in text or "之外" in text:
        boundary_bits.append("尊重用户文本中的排除范围")
    boundary_bits.append(f"聚焦：{obj}")
    if keywords:
        boundary_bits.append("关键词范围：" + "、".join(keywords[:5]))
    boundary_bits.append("不扩展到未提及的学科或年代，除非用户另行说明")
    return S1Output(
        topic_name=topic_name,
        research_object=obj,
        keywords=keywords or [topic_name],
        problem_boundary="；".join(boundary_bits),
    )


def run_s1(req: SkillRequest | dict[str, Any]) -> SkillResult:
    started = time.perf_counter()
    if isinstance(req, dict):
        req = SkillRequest(skill_code="S1", input=req)
    try:
        payload = S1Input.model_validate(req.input)
    except ValidationError as exc:
        return SkillResult(
            skill_code="S1",
            status="failed",
            error=f"输入校验失败: {exc}",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    try:
        data = structure_topic(payload.topic_text)
        # 硬约束：不能只返回自由散文
        assert data.topic_name and data.research_object and data.keywords and data.problem_boundary
        return SkillResult(
            skill_code="S1",
            status="succeeded",
            data=data.model_dump(),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        return SkillResult(
            skill_code="S1",
            status="failed",
            error=str(exc),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
