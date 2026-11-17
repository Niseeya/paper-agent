"""模型与提示词：优先读库（管理端可改）；库空时用工厂默认值种子一次。

密钥不进前端明文：列表接口只返回脱敏与 api_key_set。
环境变量仅作为首次种子来源，运行时以库内启用配置为准。
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.adapters.chat import ChatModelAdapter
from backend.app.models.system_config import ModelConfig, PromptVersion

# 仅用于库空时首次写入；之后以管理端保存内容为准
FACTORY_CHAT = {
    "kind": "chat",
    "name": "default",
    "endpoint": "https://api.deepseek.com",
    "model_name": "deepseek-chat",
    "notes": "OpenAI 兼容对话接口（如 DeepSeek）",
}

FACTORY_PROMPTS: list[dict[str, str]] = [
    {
        "skill_code": "S8",
        "prompt_key": "system",
        "title": "章节写作系统提示",
        "content": (
            "你是学术论文写作助手。只能使用给定 evidence 列表写作，禁止编造文献与库外题名/作者/年份。"
            "必须按「提出问题→分述证据→综合小结」组织，段落之间要有逻辑衔接。"
            "若提供了前文摘要，本节开头需自然承接，避免与已写章节简单重复。"
            "正式引用只能使用 evidence 中的 id，写成 [C1]；citation_ids 必须与正文标记一致。"
            "不要改动证据中的关键事实与数字。证据不足时不要硬加引用。输出 JSON："
            '{"paragraphs":[{"text":"...","citation_ids":["C1"]}]}'
        ),
    },
    {
        "skill_code": "S7",
        "prompt_key": "system",
        "title": "大纲生成系统提示",
        "content": (
            "你是学术论文大纲助手。根据研究目标与论文类型，生成可编辑的一至三级大纲。"
            "每个节点必须有 title 与 intent（写作意图）。不要编造库外文献。"
            "输出 JSON："
            '{"topic_name":"...","nodes":[{"id":"n1","level":1,"title":"1 绪论",'
            '"intent":"...","children":[{"id":"n1-1","level":2,"title":"1.1 ...","intent":"...","children":[]}]}]}'
            "必须至少包含 level=1、2、3 各一层。"
        ),
    },
    {
        "skill_code": "polish",
        "prompt_key": "system",
        "title": "润色系统提示",
        "content": (
            "你是学术润色助手。保持原意与结论方向，不改数字、专有名词与引用标记（如 [C1]）。"
            "禁止降重、洗稿或规避查重。按给定档位润色：light / academic / deep。"
            "只输出润色后的正文，不要解释。"
        ),
    },
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def mask_api_key(key: str) -> str:
    key = (key or "").strip()
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:3]}****{key[-4:]}"


def seed_llm_settings(db: Session) -> None:
    """库空时写入工厂默认；API Key 可从环境变量 LLM_API_KEY 种子一次。"""
    chat = db.scalars(
        select(ModelConfig).where(ModelConfig.kind == "chat", ModelConfig.name == "default")
    ).first()
    if not chat:
        db.add(
            ModelConfig(
                id=uuid.uuid4().hex,
                kind=FACTORY_CHAT["kind"],
                name=FACTORY_CHAT["name"],
                endpoint=os.getenv("LLM_ENDPOINT", "") or FACTORY_CHAT["endpoint"],
                api_key=os.getenv("LLM_API_KEY", "") or "",
                model_name=os.getenv("LLM_MODEL", "") or FACTORY_CHAT["model_name"],
                enabled=True,
                notes=FACTORY_CHAT["notes"],
                updated_at=_now(),
            )
        )
    for item in FACTORY_PROMPTS:
        exists = db.scalars(
            select(PromptVersion).where(
                PromptVersion.skill_code == item["skill_code"],
                PromptVersion.prompt_key == item["prompt_key"],
                PromptVersion.is_active.is_(True),
            )
        ).first()
        if exists:
            continue
        db.add(
            PromptVersion(
                id=uuid.uuid4().hex,
                skill_code=item["skill_code"],
                prompt_key=item["prompt_key"],
                title=item["title"],
                content=item["content"],
                version=1,
                is_active=True,
                updated_at=_now(),
            )
        )
    db.commit()


def get_active_model(db: Session, kind: str = "chat") -> ModelConfig | None:
    return db.scalars(
        select(ModelConfig)
        .where(ModelConfig.kind == kind, ModelConfig.enabled.is_(True))
        .order_by(ModelConfig.updated_at.desc())
    ).first()


def model_public_view(cfg: ModelConfig) -> dict[str, Any]:
    return {
        "id": cfg.id,
        "kind": cfg.kind,
        "name": cfg.name,
        "endpoint": cfg.endpoint,
        "model_name": cfg.model_name,
        "enabled": cfg.enabled,
        "notes": cfg.notes,
        "api_key_set": bool((cfg.api_key or "").strip()),
        "api_key_masked": mask_api_key(cfg.api_key or ""),
        "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None,
        "updated_by": cfg.updated_by,
    }


def get_active_prompt(db: Session, skill_code: str, prompt_key: str = "system") -> str:
    row = db.scalars(
        select(PromptVersion)
        .where(
            PromptVersion.skill_code == skill_code,
            PromptVersion.prompt_key == prompt_key,
            PromptVersion.is_active.is_(True),
        )
        .order_by(PromptVersion.version.desc())
    ).first()
    if row and row.content.strip():
        return row.content
    for item in FACTORY_PROMPTS:
        if item["skill_code"] == skill_code and item["prompt_key"] == prompt_key:
            return item["content"]
    return ""


def prompt_public_view(row: PromptVersion) -> dict[str, Any]:
    return {
        "id": row.id,
        "skill_code": row.skill_code,
        "prompt_key": row.prompt_key,
        "title": row.title,
        "content": row.content,
        "version": row.version,
        "is_active": row.is_active,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "updated_by": row.updated_by,
    }


def build_chat_adapter(db: Session | None = None) -> ChatModelAdapter:
    """从库构建对话适配器；无库/未配置时返回不可用适配器。"""
    if db is None:
        from backend.app.db import SessionLocal

        session = SessionLocal()
        try:
            return build_chat_adapter(session)
        finally:
            session.close()
    cfg = get_active_model(db, "chat")
    if not cfg:
        return ChatModelAdapter(endpoint="", api_key="", model="")
    return ChatModelAdapter(
        endpoint=cfg.endpoint or "",
        api_key=cfg.api_key or "",
        model=cfg.model_name or "",
    )


def upsert_chat_model(
    db: Session,
    *,
    endpoint: str,
    model_name: str,
    api_key: str | None,
    enabled: bool = True,
    notes: str = "",
    user_id: str | None = None,
) -> ModelConfig:
    cfg = db.scalars(
        select(ModelConfig).where(ModelConfig.kind == "chat", ModelConfig.name == "default")
    ).first()
    if not cfg:
        cfg = ModelConfig(
            id=uuid.uuid4().hex,
            kind="chat",
            name="default",
            endpoint=endpoint,
            api_key=api_key or "",
            model_name=model_name,
            enabled=enabled,
            notes=notes,
            updated_at=_now(),
            updated_by=user_id,
        )
        db.add(cfg)
    else:
        cfg.endpoint = endpoint
        cfg.model_name = model_name
        cfg.enabled = enabled
        cfg.notes = notes
        # 空字符串表示不改动已有密钥
        if api_key is not None and api_key.strip() != "":
            cfg.api_key = api_key.strip()
        cfg.updated_at = _now()
        cfg.updated_by = user_id
    db.commit()
    db.refresh(cfg)
    return cfg


def save_prompt(
    db: Session,
    *,
    skill_code: str,
    prompt_key: str,
    content: str,
    title: str = "",
    user_id: str | None = None,
) -> PromptVersion:
    current = db.scalars(
        select(PromptVersion)
        .where(
            PromptVersion.skill_code == skill_code,
            PromptVersion.prompt_key == prompt_key,
            PromptVersion.is_active.is_(True),
        )
        .order_by(PromptVersion.version.desc())
    ).first()
    next_ver = (current.version + 1) if current else 1
    if current:
        current.is_active = False
    row = PromptVersion(
        id=uuid.uuid4().hex,
        skill_code=skill_code,
        prompt_key=prompt_key,
        title=title or (current.title if current else f"{skill_code}.{prompt_key}"),
        content=content,
        version=next_ver,
        is_active=True,
        updated_at=_now(),
        updated_by=user_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
