"""S7 大纲：研究目标 -> 可编辑大纲（一至三级标题 + 每节写作意图）。

优先使用管理端配置的对话模型与提示词；失败时回退模板大纲。
"""

from __future__ import annotations

import json
import re
import time
import uuid
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from backend.app.adapters.chat import ChatNotConfigured, get_chat_adapter
from backend.app.db import SessionLocal
from backend.app.services.llm_settings import get_active_prompt
from backend.app.skills.base import SkillRequest, SkillResult
from backend.app.skills.s1_topic import structure_topic


class S7Input(BaseModel):
    research_goal: str = Field(min_length=4)
    paper_type: str = "综述"  # 综述 | 实证研究 | 设计与实现
    related_paper_ids: list[str] = Field(default_factory=list)


class OutlineNode(BaseModel):
    id: str
    level: int  # 1/2/3
    title: str
    intent: str
    related_paper_ids: list[str] = Field(default_factory=list)
    children: list["OutlineNode"] = Field(default_factory=list)


class S7Output(BaseModel):
    paper_type: str
    topic_name: str
    nodes: list[OutlineNode]
    confirmed: bool = False
    writer: str = "template"  # template | llm


_TEMPLATES: dict[str, list[tuple[str, str, list[tuple[str, str]]]]] = {
    "综述": [
        ("绪论", "交代选题背景、研究问题与论文结构", [("研究背景", "说明领域现状与问题提出"), ("研究意义", "阐明理论与实践价值")]),
        ("文献综述", "按主题梳理已有研究并标注依据文献", [("主要流派", "归纳代表性路径"), ("争议与不足", "指出分歧与薄弱点")]),
        ("研究空白与问题提出", "在证据约束下提出本文聚焦问题", [("空白归纳", "汇总库内覆盖不足处"), ("研究问题", "明确可回答的问题边界")]),
        ("分析框架", "给出分析维度与章节安排", [("分析维度", "说明对比/分类维度"), ("章节安排", "对应后续各章意图")]),
        ("结论与展望", "总结发现并给出建议型展望", [("主要结论", "回扣研究问题"), ("后续研究", "给出可检验的建议")]),
    ],
    "实证研究": [
        ("绪论", "提出研究问题与假设边界", [("问题陈述", "明确研究对象与范围")]),
        ("文献与假设", "综述相关工作并推导假设", [("文献基础", "列出依据文献"), ("研究假设", "给出可检验命题")]),
        ("方法", "说明样本、数据与分析步骤", [("样本与数据", "交代来源与筛选"), ("分析步骤", "写明可复现流程")]),
        ("结果", "呈现主要发现并绑定证据", [("描述性结果", "汇总关键发现"), ("假设检验", "对照假设陈述结果")]),
        ("讨论与结论", "解释结果并声明局限", [("讨论", "对照文献解释"), ("结论与局限", "总结并标明不足")]),
    ],
    "设计与实现": [
        ("绪论", "说明问题背景与建设目标", [("需求分析", "列出功能与约束")]),
        ("相关工作", "对比已有系统与方法", [("方案对比", "用证据说明差异")]),
        ("系统设计", "给出架构与关键模块", [("总体架构", "描述模块与数据流"), ("关键设计", "详述核心模块意图")]),
        ("实现与验证", "说明实现要点与验证结果", [("实现要点", "技术选型与难点"), ("验证", "用例与指标")]),
        ("总结", "回顾贡献与后续工作", [("贡献", "对应目标"), ("后续工作", "给出建议")]),
    ],
}


def _nid() -> str:
    return uuid.uuid4().hex[:12]


def build_outline(goal: str, paper_type: str, related: list[str]) -> S7Output:
    topic = structure_topic(goal)
    tpl = _TEMPLATES.get(paper_type) or _TEMPLATES["综述"]
    nodes: list[OutlineNode] = []
    for i, (title, intent, children) in enumerate(tpl, start=1):
        child_nodes = [
            OutlineNode(
                id=_nid(),
                level=2,
                title=f"{i}.{j} {ct}",
                intent=ci,
                related_paper_ids=related[:3],
            )
            for j, (ct, ci) in enumerate(children, start=1)
        ]
        if child_nodes and i == 2:
            child_nodes[0].children = [
                OutlineNode(
                    id=_nid(),
                    level=3,
                    title=f"{i}.1.1 代表性文献要点",
                    intent="用库内证据概括要点，空缺写库内未找到",
                    related_paper_ids=related[:2],
                )
            ]
        nodes.append(
            OutlineNode(
                id=_nid(),
                level=1,
                title=f"{i} {title}",
                intent=f"{intent}；围绕主题「{topic.topic_name}」展开",
                related_paper_ids=related[:4],
                children=child_nodes,
            )
        )
    return S7Output(
        paper_type=paper_type,
        topic_name=topic.topic_name,
        nodes=nodes,
        confirmed=False,
        writer="template",
    )


def _normalize_nodes(raw: list[Any], related: list[str], *, level: int = 1) -> list[OutlineNode]:
    if not raw or level > 3:
        return []
    nodes: list[OutlineNode] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        intent = str(item.get("intent") or "").strip()
        if not title or not intent:
            continue
        children = _normalize_nodes(list(item.get("children") or []), related, level=level + 1)
        nodes.append(
            OutlineNode(
                id=str(item.get("id") or "").strip() or _nid(),
                level=level,
                title=title,
                intent=intent,
                related_paper_ids=related[: max(1, 5 - level)],
                children=children,
            )
        )
    return nodes


def _levels(nodes: list[OutlineNode]) -> set[int]:
    found: set[int] = set()

    def walk(ns: list[OutlineNode]):
        for n in ns:
            found.add(n.level)
            walk(n.children)

    walk(nodes)
    return found


def build_outline_with_llm(goal: str, paper_type: str, related: list[str], system_prompt: str) -> S7Output | None:
    adapter = get_chat_adapter()
    if not adapter.available() or not (system_prompt or "").strip():
        return None
    user = {
        "research_goal": goal,
        "paper_type": paper_type,
        "related_paper_ids": related[:8],
    }
    try:
        raw = adapter.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
    except (ChatNotConfigured, Exception):
        return None
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    nodes = _normalize_nodes(list(data.get("nodes") or []), related)
    if not nodes or not ({1, 2, 3} <= _levels(nodes)):
        return None
    topic_name = str(data.get("topic_name") or "").strip() or structure_topic(goal).topic_name
    return S7Output(
        paper_type=paper_type,
        topic_name=topic_name,
        nodes=nodes,
        confirmed=False,
        writer="llm",
    )


def run_s7(req: SkillRequest | dict[str, Any]) -> SkillResult:
    started = time.perf_counter()
    if isinstance(req, dict):
        req = SkillRequest(skill_code="S7", input=req)
    try:
        payload = S7Input.model_validate(req.input)
    except ValidationError as exc:
        return SkillResult(
            skill_code="S7",
            status="failed",
            error=f"输入校验失败: {exc}",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    try:
        db = SessionLocal()
        try:
            system_prompt = get_active_prompt(db, "S7", "system")
        finally:
            db.close()
        out = build_outline_with_llm(
            payload.research_goal,
            payload.paper_type,
            payload.related_paper_ids,
            system_prompt,
        )
        if out is None:
            out = build_outline(payload.research_goal, payload.paper_type, payload.related_paper_ids)
        levels = _levels(out.nodes)
        assert 1 in levels and 2 in levels and 3 in levels
        return SkillResult(
            skill_code="S7",
            status="succeeded",
            data=out.model_dump(),
            model_id=get_chat_adapter().model_id if out.writer == "llm" else "template-s7",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        return SkillResult(
            skill_code="S7",
            status="failed",
            error=str(exc),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
