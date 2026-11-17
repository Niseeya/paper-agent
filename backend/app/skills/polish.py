"""润色 polish：轻度/学术/深度；拒绝对降重请求；不改数字、专有名词、引用与结论方向。

有管理端配置的对话模型与提示词时走 LLM；否则回退规则润色。
"""

from __future__ import annotations

import re
import time
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from backend.app.adapters.chat import ChatNotConfigured, get_chat_adapter
from backend.app.db import SessionLocal
from backend.app.services.llm_settings import get_active_prompt
from backend.app.skills.base import SkillRequest, SkillResult

REJECT_REWRITE = re.compile(r"(降重|降重率|查重|规避相似性|洗稿|改写避查)")


class PolishInput(BaseModel):
    text: str = Field(min_length=1)
    level: str = "academic"  # light | academic | deep | bilingual
    user_request: str = ""


class DiffItem(BaseModel):
    original: str
    polished: str
    reason: str


class PolishOutput(BaseModel):
    level: str
    original: str
    polished: str
    diffs: list[DiffItem]
    confirmed: bool = False
    rejected: bool = False
    reject_reason: str | None = None
    writer: str = "template"  # template | llm


def _protect_tokens(text: str) -> tuple[str, dict[str, str]]:
    mapping: dict[str, str] = {}
    idx = 0

    def repl(m: re.Match) -> str:
        nonlocal idx
        key = f"__KEEP{idx}__"
        mapping[key] = m.group(0)
        idx += 1
        return key

    protected = re.sub(r"\[[A-Za-z]?\d+\]|\d+(\.\d+)?%?|(?:19|20)\d{2}", repl, text)
    return protected, mapping


def _restore(text: str, mapping: dict[str, str]) -> str:
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text


def _polish_text_rules(text: str, level: str) -> tuple[str, list[DiffItem]]:
    protected, mapping = _protect_tokens(text)
    polished = protected
    diffs: list[DiffItem] = []

    replacements = [
        ("进行了", "开展了", "学术措辞"),
        ("非常重要", "至关重要", "学术措辞"),
        ("很多", "诸多", "学术措辞"),
        ("但是", "然而", "衔接"),
        ("所以", "因此", "衔接"),
    ]
    if level == "light":
        replacements = replacements[:2]
    elif level == "deep":
        replacements = replacements + [("我们认为", "本文认为", "主语规范"), ("可以看出", "由此可见", "学术措辞")]

    for a, b, reason in replacements:
        if a in polished:
            polished2 = polished.replace(a, b)
            if polished2 != polished:
                diffs.append(DiffItem(original=a, polished=b, reason=reason))
                polished = polished2

    polished = _restore(polished, mapping)
    if polished == text and not diffs:
        diffs.append(DiffItem(original=text[:40], polished=polished[:40], reason="保持原意，仅做最小调整"))
    return polished, diffs


def _polish_with_llm(text: str, level: str, user_request: str, system_prompt: str) -> str | None:
    adapter = get_chat_adapter()
    if not adapter.available() or not (system_prompt or "").strip():
        return None
    user = (
        f"档位：{level}\n"
        f"附加说明：{user_request or '无'}\n"
        f"原文：\n{text}"
    )
    try:
        return adapter.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=min(4000, max(800, len(text) + 400)),
        )
    except (ChatNotConfigured, Exception):
        return None


def _guard_invariants(original: str, polished: str) -> tuple[str, list[DiffItem] | None]:
    """数字与引用标记必须保留；否则回退原文。"""
    nums_src = re.findall(r"\d+(?:\.\d+)?%?", original)
    nums_dst = re.findall(r"\d+(?:\.\d+)?%?", polished)
    if nums_src != nums_dst:
        return original, [DiffItem(original=original, polished=original, reason="检测到数字变化，已回退原文")]
    cites_src = re.findall(r"\[[A-Za-z]?\d+\]", original)
    cites_dst = re.findall(r"\[[A-Za-z]?\d+\]", polished)
    if cites_src != cites_dst:
        return original, [DiffItem(original=original, polished=original, reason="检测到引用标记变化，已回退原文")]
    return polished, None


def run_polish(req: SkillRequest | dict[str, Any]) -> SkillResult:
    started = time.perf_counter()
    if isinstance(req, dict):
        req = SkillRequest(skill_code="polish", input=req)
    try:
        payload = PolishInput.model_validate(req.input)
    except ValidationError as exc:
        return SkillResult(
            skill_code="polish",
            status="failed",
            error=f"输入校验失败: {exc}",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    if REJECT_REWRITE.search(payload.user_request) or REJECT_REWRITE.search(payload.text[:200]):
        out = PolishOutput(
            level=payload.level,
            original=payload.text,
            polished=payload.text,
            diffs=[],
            confirmed=False,
            rejected=True,
            reject_reason="拒绝降重/规避查重请求，原文保持不变；可改为学术润色",
            writer="template",
        )
        return SkillResult(
            skill_code="polish",
            status="succeeded",
            data=out.model_dump(),
            warnings=[out.reject_reason or ""],
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    writer = "template"
    db = SessionLocal()
    try:
        system_prompt = get_active_prompt(db, "polish", "system")
    finally:
        db.close()

    llm_text = _polish_with_llm(payload.text, payload.level, payload.user_request, system_prompt)
    if llm_text:
        polished, bad = _guard_invariants(payload.text, llm_text.strip())
        if bad is None:
            writer = "llm"
            diffs = [DiffItem(original=payload.text[:80], polished=polished[:80], reason="大模型学术润色（可对照确认）")]
        else:
            polished, diffs = payload.text, bad
    else:
        polished, diffs = _polish_text_rules(payload.text, payload.level)
        polished, bad = _guard_invariants(payload.text, polished)
        if bad is not None:
            polished, diffs = payload.text, bad

    out = PolishOutput(
        level=payload.level,
        original=payload.text,
        polished=polished,
        diffs=diffs,
        confirmed=False,
        writer=writer,
    )
    return SkillResult(
        skill_code="polish",
        status="succeeded",
        data=out.model_dump(),
        model_id=get_chat_adapter().model_id if writer == "llm" else "template-polish",
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
