"""项目主路径：大纲 → 分节写作 → 润色 → 核查 → 导出。

成稿原则：
- 大纲确认后，按大纲一级章节驱动写作，禁止手填漂移为唯一路径。
- 写作时传入研究目标、本节意图、已写章节摘要，保证跨节衔接。
- 润色按节进行并保留 citations，确认时不压扁章节结构。
- 导出汇总参考文献表。
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.project_content import ProjectArtifact
from backend.app.models.user import Project
from backend.app.skills.polish import run_polish
from backend.app.skills.s2_retrieve import keyword_search
from backend.app.skills.s7_outline import OutlineNode, S7Output, run_s7
from backend.app.skills.s8_write import run_s8
from backend.app.skills.s9_check import run_s9
from backend.app.skills.s10_export import run_s10

ROOT = Path(__file__).resolve().parents[3]
EXPORT_DIR = ROOT / "data" / "exports"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _next_version(db: Session, project_id: str, kind: str) -> int:
    rows = list(
        db.scalars(
            select(ProjectArtifact)
            .where(ProjectArtifact.project_id == project_id, ProjectArtifact.kind == kind)
            .order_by(ProjectArtifact.version.desc())
            .limit(1)
        ).all()
    )
    return (rows[0].version + 1) if rows else 1


def latest_artifact(db: Session, project_id: str, kind: str) -> ProjectArtifact | None:
    return db.scalars(
        select(ProjectArtifact)
        .where(ProjectArtifact.project_id == project_id, ProjectArtifact.kind == kind)
        .order_by(ProjectArtifact.version.desc())
        .limit(1)
    ).first()


def save_artifact(
    db: Session,
    project: Project,
    *,
    kind: str,
    payload: dict,
    title: str = "",
    confirmed: bool = False,
) -> ProjectArtifact:
    art = ProjectArtifact(
        id=uuid.uuid4().hex,
        project_id=project.id,
        kind=kind,
        version=_next_version(db, project.id, kind),
        title=title or project.title,
        payload=payload,
        confirmed=confirmed,
        created_at=_now(),
    )
    db.add(art)
    project.updated_at = _now()
    db.commit()
    db.refresh(art)
    return art


def _research_goal(project: Project) -> str:
    meta = project.meta or {}
    return (meta.get("research_goal") or project.title or "").strip()


def _flatten_outline_chapters(outline_payload: dict | None) -> list[dict[str, Any]]:
    """可写单元：一级章节（含意图与关联文献）。"""
    if not outline_payload:
        return []
    chapters: list[dict[str, Any]] = []
    for node in outline_payload.get("nodes") or []:
        if int(node.get("level") or 1) != 1:
            continue
        child_intents = [c.get("intent") or "" for c in (node.get("children") or [])]
        intent = node.get("intent") or ""
        if child_intents:
            intent = intent + "；覆盖：" + "；".join(x for x in child_intents if x)
        chapters.append(
            {
                "id": node.get("id") or "",
                "title": (node.get("title") or "").strip(),
                "intent": intent,
                "related_paper_ids": list(node.get("related_paper_ids") or []),
            }
        )
    return [c for c in chapters if c["title"]]


def writing_plan(db: Session, project: Project) -> dict[str, Any]:
    outline = latest_artifact(db, project.id, "outline")
    doc = latest_artifact(db, project.id, "document")
    chapters = _flatten_outline_chapters(outline.payload if outline else None)
    written_titles = {
        (s.get("title") or "").strip()
        for s in ((doc.payload or {}).get("sections") or [] if doc else [])
    }
    items = []
    for ch in chapters:
        items.append(
            {
                **ch,
                "written": ch["title"] in written_titles,
            }
        )
    return {
        "outline_confirmed": bool(project.outline_confirmed),
        "research_goal": _research_goal(project),
        "chapters": items,
        "written_count": sum(1 for x in items if x["written"]),
        "total": len(items),
    }


def flow_step_index(db: Session, project: Project) -> int:
    """主流程步骤：0检索 1大纲 2写作 3润色 4核查 5导出。"""
    plan = writing_plan(db, project)
    if not latest_artifact(db, project.id, "outline") or not project.outline_confirmed:
        if (project.status or "draft") in ("draft", "preparing") and not latest_artifact(
            db, project.id, "outline"
        ):
            # 新建后先鼓励检索，仍可跳过直接做大纲
            return 0
        return 1
    if plan["total"] and plan["written_count"] < plan["total"]:
        return 2
    check = latest_artifact(db, project.id, "citation_check")
    polish = latest_artifact(db, project.id, "polish")
    if not polish or not polish.confirmed:
        # 正文齐后优先润色；若用户已直接核查则进入核查步
        if check:
            return 4 if not (check.payload or {}).get("passed") else 5
        return 3
    if not check:
        return 4
    if not (check.payload or {}).get("passed"):
        return 4
    return 5


def next_step(db: Session, project: Project) -> dict[str, str]:
    """按项目状态给出唯一主 CTA。"""
    plan = writing_plan(db, project)
    status = project.status or "draft"
    step = flow_step_index(db, project)
    if step == 0:
        return {
            "code": "search",
            "path": "search",
            "label": "检索文献",
            "reason": "先在公用知识库检索相关证据，再生成大纲",
            "step": 0,
        }
    if status in ("draft", "preparing") or not latest_artifact(db, project.id, "outline"):
        return {
            "code": "outline",
            "path": "outline",
            "label": "生成并确认大纲",
            "reason": "先用 S7 形成可编辑大纲，确认后才能写作",
            "step": 1,
        }
    if status == "outline_pending" or not project.outline_confirmed:
        return {
            "code": "confirm_outline",
            "path": "outline",
            "label": "确认大纲",
            "reason": "大纲未确认，不能生成章节",
            "step": 1,
        }
    if plan["total"] and plan["written_count"] < plan["total"]:
        return {
            "code": "write",
            "path": "editor",
            "label": f"继续写作（{plan['written_count']}/{plan['total']}）",
            "reason": "按大纲逐章生成带真实引用的正文",
            "step": 2,
        }
    check = latest_artifact(db, project.id, "citation_check")
    polish = latest_artifact(db, project.id, "polish")
    if not polish or not polish.confirmed:
        if check and (check.payload or {}).get("passed"):
            return {
                "code": "export",
                "path": "export",
                "label": "导出定稿",
                "reason": "引用核查已通过，可导出 DOCX/PDF",
                "step": 5,
            }
        if check and not (check.payload or {}).get("passed"):
            return {
                "code": "fix_citations",
                "path": "citations",
                "label": "处理核查问题",
                "reason": "存在未通过的引用或逻辑问题，定稿前需处理",
                "step": 4,
            }
        return {
            "code": "polish",
            "path": "polish",
            "label": "润色对照并确认",
            "reason": "正文已齐，先润色再核查；确认前不替换正文",
            "step": 3,
        }
    if not check:
        return {
            "code": "check",
            "path": "citations",
            "label": "运行引用核查",
            "reason": "润色已确认，请核查 L1/L2 后再定稿",
            "step": 4,
        }
    if not (check.payload or {}).get("passed"):
        return {
            "code": "fix_citations",
            "path": "citations",
            "label": "处理核查问题",
            "reason": "存在未通过的引用或逻辑问题，定稿前需处理",
            "step": 4,
        }
    return {
        "code": "export",
        "path": "export",
        "label": "导出定稿",
        "reason": "引用核查已通过，可导出 DOCX/PDF",
        "step": 5,
    }


def generate_outline(db: Session, project: Project, research_goal: str | None = None) -> ProjectArtifact:
    goal = (research_goal or _research_goal(project) or project.title).strip()
    related: list[str] = []
    try:
        hits = keyword_search(db, goal, top_k=6)
        related = [h.paper_id for h in hits]
    except Exception:  # noqa: BLE001
        related = []
    result = run_s7(
        {
            "research_goal": goal,
            "paper_type": project.paper_type,
            "related_paper_ids": related,
        }
    )
    if result.status != "succeeded":
        raise RuntimeError(result.error or "大纲生成失败")
    project.status = "outline_pending"
    project.outline_confirmed = False
    meta = dict(project.meta or {})
    meta["research_goal"] = goal
    meta["related_paper_ids"] = related
    project.meta = meta
    return save_artifact(db, project, kind="outline", payload=result.data, title=goal, confirmed=False)


def _normalize_outline_nodes(raw_nodes: list[dict[str, Any]], *, level: int = 1) -> list[OutlineNode]:
    """清洗手工编辑结果：补 id、校正 level（1～3）、校验标题与意图。"""
    if not raw_nodes:
        return []
    if level > 3:
        raise ValueError("大纲最多三级标题")
    nodes: list[OutlineNode] = []
    for raw in raw_nodes:
        title = str(raw.get("title") or "").strip()
        intent = str(raw.get("intent") or "").strip()
        if not title:
            raise ValueError("章节标题不能为空")
        if not intent:
            raise ValueError(f"章节「{title}」缺少写作意图")
        node_id = str(raw.get("id") or "").strip() or uuid.uuid4().hex
        related = [str(x) for x in (raw.get("related_paper_ids") or []) if x]
        children = _normalize_outline_nodes(list(raw.get("children") or []), level=level + 1)
        nodes.append(
            OutlineNode(
                id=node_id,
                level=level,
                title=title,
                intent=intent,
                related_paper_ids=related,
                children=children,
            )
        )
    return nodes


def update_outline(
    db: Session,
    project: Project,
    *,
    nodes: list[dict[str, Any]],
    topic_name: str | None = None,
    paper_type: str | None = None,
) -> ProjectArtifact:
    """作者手工修改大纲：另存为新版本，并取消确认（需重新确认后才能批量写作）。"""
    if not nodes:
        raise ValueError("大纲至少需要一个章节")
    normalized = _normalize_outline_nodes(nodes)
    prev = latest_artifact(db, project.id, "outline")
    prev_payload = dict(prev.payload or {}) if prev else {}
    out = S7Output(
        paper_type=paper_type or prev_payload.get("paper_type") or project.paper_type or "综述",
        topic_name=topic_name or prev_payload.get("topic_name") or project.title,
        nodes=normalized,
        confirmed=False,
    )
    project.status = "outline_pending"
    project.outline_confirmed = False
    project.updated_at = _now()
    return save_artifact(
        db,
        project,
        kind="outline",
        payload=out.model_dump(),
        title=_research_goal(project) or project.title,
        confirmed=False,
    )


def confirm_outline_artifact(db: Session, project: Project, version: int) -> ProjectArtifact:
    art = db.scalars(
        select(ProjectArtifact).where(
            ProjectArtifact.project_id == project.id,
            ProjectArtifact.kind == "outline",
            ProjectArtifact.version == version,
        )
    ).first()
    if not art:
        raise LookupError("大纲版本不存在")
    art.confirmed = True
    payload = dict(art.payload or {})
    payload["confirmed"] = True
    art.payload = payload
    project.outline_confirmed = True
    project.status = "writing"
    project.updated_at = _now()
    meta = dict(project.meta or {})
    meta["outline_version"] = version
    if not meta.get("research_goal"):
        meta["research_goal"] = art.title or project.title
    project.meta = meta
    db.commit()
    db.refresh(art)
    return art


def _prior_summary(
    sections: list[dict],
    *,
    exclude_title: str = "",
    outline_titles: list[str] | None = None,
    limit: int = 2,
) -> str:
    by_title = {(s.get("title") or "").strip(): s for s in sections}
    # 只承接大纲顺序中「本节之前」的章节，避免后章摘要串进前章
    if outline_titles and exclude_title in outline_titles:
        idx = outline_titles.index(exclude_title)
        candidates = outline_titles[:idx]
    else:
        candidates = [t for t in by_title if t and t != exclude_title]

    bits: list[str] = []
    for title in candidates[-limit:]:
        sec = by_title.get(title)
        if not sec:
            continue
        paras = [p for p in (sec.get("paragraphs") or []) if p]
        if not paras:
            continue
        head = paras[0]
        # 跳过纯承接句，优先取含实质内容的句子
        for p in paras:
            if "承接前文" in p[:20] and len(paras) > 1:
                continue
            head = p
            break
        if "。" in head:
            head = head.split("。")[0] + "。"
        head = head[:64].rstrip("。") + "。"
        bits.append(f"「{title}」：{head}")
    return " ".join(bits)


def _section_role(title: str) -> str:
    t = title or ""
    if any(k in t for k in ("结论", "展望", "总结")):
        return "conclusion"
    if any(k in t for k in ("绪论", "引言")) or re.fullmatch(r"[\d\s.]*研究背景.*", t):
        return "intro"
    if any(k in t for k in ("方法", "设计", "实现", "分析框架")):
        return "method"
    return "body"


def _ordered_sections(existing: list[dict], outline_chapters: list[dict]) -> list[dict]:
    """按大纲顺序排列已写章节，大纲外章节附后。优先按 section_id 对齐。"""
    by_id = {(s.get("section_id") or "").strip(): s for s in existing if (s.get("section_id") or "").strip()}
    by_title = {(s.get("title") or "").strip(): s for s in existing}
    ordered: list[dict] = []
    seen: set[str] = set()
    for ch in outline_chapters:
        title = ch["title"]
        cid = (ch.get("id") or "").strip()
        sec = (by_id.get(cid) if cid else None) or by_title.get(title)
        if sec:
            # 回填 section_id，便于后续精确重写本节
            if cid and not sec.get("section_id"):
                sec = {**sec, "section_id": cid}
            ordered.append(sec)
            seen.add((sec.get("section_id") or "") + "|" + (sec.get("title") or "").strip())
    for s in existing:
        key = (s.get("section_id") or "") + "|" + (s.get("title") or "").strip()
        if key not in seen:
            ordered.append(s)
            seen.add(key)
    return ordered


def _is_same_section(sec: dict, *, section_id: str, section_title: str) -> bool:
    sid = (sec.get("section_id") or "").strip()
    title = (sec.get("title") or "").strip()
    if section_id and sid and sid == section_id:
        return True
    return bool(section_title) and title == section_title


def write_section(
    db: Session,
    project: Project,
    *,
    section_title: str,
    writing_intent: str = "",
    related_paper_ids: list[str] | None = None,
    section_id: str | None = None,
) -> ProjectArtifact:
    """只重写/生成指定一节，保留文档中其他章节不变。"""
    if not project.outline_confirmed:
        raise PermissionError("大纲未确认，不能批量生成章节")

    outline = latest_artifact(db, project.id, "outline")
    chapters = _flatten_outline_chapters(outline.payload if outline else None)
    matched = None
    if section_id:
        matched = next((c for c in chapters if c.get("id") == section_id), None)
    if matched is None:
        matched = next((c for c in chapters if c["title"] == section_title), None)
    title = (matched["title"] if matched else section_title or "").strip()
    if not title:
        raise ValueError("缺少章节标题，无法写作")
    sid = (matched.get("id") if matched else None) or (section_id or "") or ""
    intent = writing_intent or (matched["intent"] if matched else "")
    related = list(related_paper_ids or (matched["related_paper_ids"] if matched else []) or [])
    if not related:
        related = list((project.meta or {}).get("related_paper_ids") or [])

    doc = latest_artifact(db, project.id, "document")
    sections = list((doc.payload or {}).get("sections") or []) if doc else []
    prior = _prior_summary(
        sections,
        exclude_title=title,
        outline_titles=[c["title"] for c in chapters],
    )
    used_ids: list[str] = []
    for sec in sections:
        if _is_same_section(sec, section_id=sid, section_title=title):
            continue
        for c in sec.get("citations") or []:
            pid = c.get("paper_id")
            if pid and pid not in used_ids:
                used_ids.append(pid)

    result = run_s8(
        {
            "section_title": title,
            "writing_intent": intent,
            "outline_confirmed": True,
            "research_goal": _research_goal(project),
            "prior_sections_summary": prior,
            "related_paper_ids": related,
            "exclude_paper_ids": used_ids,
            "section_role": _section_role(title),
            "write_scope": "single_section",
        },
        db=db,
    )
    if result.status != "succeeded":
        raise RuntimeError(result.error or "章节写作失败")

    # 精确替换本节，其它章节原样保留
    kept = [s for s in sections if not _is_same_section(s, section_id=sid, section_title=title)]
    paragraphs = [p.get("text", "") for p in result.data.get("paragraphs") or []]
    kept.append(
        {
            "section_id": sid,
            "title": title,
            "intent": intent,
            "paragraphs": paragraphs,
            "citations": result.data.get("citations") or [],
            "writer": result.data.get("writer"),
            "raw": result.data,
        }
    )
    sections = _ordered_sections(kept, chapters)
    payload = {
        "title": project.title,
        "research_goal": _research_goal(project),
        "sections": sections,
        "last_section": title,
        "last_section_id": sid,
    }
    project.status = "writing"
    return save_artifact(db, project, kind="document", payload=payload, title=project.title)


def write_missing_chapters(db: Session, project: Project, *, max_chapters: int = 8) -> ProjectArtifact:
    """按大纲顺序生成尚未写作的一级章节（不覆盖已写）。"""
    if not project.outline_confirmed:
        raise PermissionError("大纲未确认，不能批量生成章节")
    plan = writing_plan(db, project)
    missing = [c for c in plan["chapters"] if not c["written"]][:max_chapters]
    if not missing:
        doc = latest_artifact(db, project.id, "document")
        if not doc:
            raise LookupError("大纲章节均已写入，但尚无文档")
        return doc
    art = None
    for ch in missing:
        art = write_section(
            db,
            project,
            section_title=ch["title"],
            writing_intent=ch.get("intent") or "",
            related_paper_ids=ch.get("related_paper_ids") or [],
            section_id=ch.get("id") or "",
        )
    assert art is not None
    return art


def rewrite_all_chapters(db: Session, project: Project, *, max_chapters: int = 12) -> ProjectArtifact:
    """按大纲顺序重写全部一级章节（覆盖已写）。"""
    if not project.outline_confirmed:
        raise PermissionError("大纲未确认，不能批量生成章节")
    plan = writing_plan(db, project)
    targets = list(plan["chapters"] or [])[:max_chapters]
    if not targets:
        raise LookupError("大纲中没有可写章节")
    art = None
    for ch in targets:
        art = write_section(
            db,
            project,
            section_title=ch["title"],
            writing_intent=ch.get("intent") or "",
            related_paper_ids=ch.get("related_paper_ids") or [],
            section_id=ch.get("id") or "",
        )
    assert art is not None
    return art


def save_document(db: Session, project: Project, sections: list[dict]) -> ProjectArtifact:
    outline = latest_artifact(db, project.id, "outline")
    chapters = _flatten_outline_chapters(outline.payload if outline else None)
    ordered = _ordered_sections(sections, chapters)
    payload = {
        "title": project.title,
        "research_goal": _research_goal(project),
        "sections": ordered,
    }
    return save_artifact(db, project, kind="document", payload=payload, title=project.title)


def polish_document(
    db: Session,
    project: Project,
    *,
    level: str = "academic",
    user_request: str = "",
    text: str | None = None,
) -> ProjectArtifact:
    doc = latest_artifact(db, project.id, "document")
    if text is not None:
        # 兼容旧调用：整文润色，但仍尝试按空行保留
        result = run_polish({"text": text, "level": level, "user_request": user_request})
        if result.status != "succeeded":
            raise RuntimeError(result.error or "润色失败")
        return save_artifact(db, project, kind="polish", payload=result.data, title=project.title, confirmed=False)

    if not doc:
        raise LookupError("尚无正文可润色")

    sections_in = list((doc.payload or {}).get("sections") or [])
    if not sections_in:
        raise LookupError("尚无正文可润色")

    polished_sections: list[dict] = []
    all_diffs: list[dict] = []
    originals: list[str] = []
    polished_texts: list[str] = []
    rejected = False
    reject_reason = None

    for sec in sections_in:
        title = sec.get("title") or "章节"
        paras = list(sec.get("paragraphs") or [])
        originals.append(f"## {title}\n" + "\n\n".join(paras))
        if not any(p.strip() for p in paras):
            polished_sections.append(
                {
                    "title": title,
                    "paragraphs": paras,
                    "citations": sec.get("citations") or [],
                    "intent": sec.get("intent"),
                }
            )
            polished_texts.append(f"## {title}\n")
            continue

        new_paras: list[str] = []
        for para in paras:
            if not para.strip():
                new_paras.append(para)
                continue
            result = run_polish({"text": para, "level": level, "user_request": user_request})
            if result.status != "succeeded":
                raise RuntimeError(result.error or "润色失败")
            data = result.data or {}
            if data.get("rejected"):
                rejected = True
                reject_reason = data.get("reject_reason")
                polished_sections = [
                    {
                        "title": s.get("title"),
                        "paragraphs": list(s.get("paragraphs") or []),
                        "citations": s.get("citations") or [],
                        "intent": s.get("intent"),
                    }
                    for s in sections_in
                ]
                polished_texts = originals
                all_diffs = []
                new_paras = []
                break
            new_paras.append(data.get("polished") or para)
            all_diffs.extend(data.get("diffs") or [])
        if rejected:
            break
        polished_sections.append(
            {
                "title": title,
                "paragraphs": new_paras,
                "citations": sec.get("citations") or [],
                "intent": sec.get("intent"),
            }
        )
        polished_texts.append(f"## {title}\n" + "\n\n".join(new_paras))

    payload = {
        "level": level,
        "original": "\n\n".join(originals),
        "polished": "\n\n".join(polished_texts),
        "diffs": all_diffs,
        "confirmed": False,
        "rejected": rejected,
        "reject_reason": reject_reason,
        "sections": polished_sections,
        "preserve_structure": True,
    }
    return save_artifact(db, project, kind="polish", payload=payload, title=project.title, confirmed=False)


def confirm_polish(db: Session, project: Project, version: int) -> ProjectArtifact:
    art = db.scalars(
        select(ProjectArtifact).where(
            ProjectArtifact.project_id == project.id,
            ProjectArtifact.kind == "polish",
            ProjectArtifact.version == version,
        )
    ).first()
    if not art:
        raise LookupError("润色版本不存在")
    if (art.payload or {}).get("rejected"):
        raise PermissionError("该润色请求已被拒绝，不能确认替换正文")
    art.confirmed = True
    payload = dict(art.payload or {})
    payload["confirmed"] = True
    art.payload = payload

    sections = list((payload.get("sections") or []))
    if not sections:
        # 兼容旧润色记录：不毁结构——若有旧 document，仅追加提示段
        doc = latest_artifact(db, project.id, "document")
        if doc and (doc.payload or {}).get("sections"):
            sections = list((doc.payload or {}).get("sections") or [])
        else:
            polished = payload.get("polished") or ""
            sections = [{"title": "正文", "paragraphs": [p for p in polished.split("\n") if p.strip()], "citations": []}]

    outline = latest_artifact(db, project.id, "outline")
    chapters = _flatten_outline_chapters(outline.payload if outline else None)
    ordered = _ordered_sections(sections, chapters)
    save_artifact(
        db,
        project,
        kind="document",
        payload={
            "title": project.title,
            "research_goal": _research_goal(project),
            "sections": ordered,
            "from_polish_version": version,
        },
        title=project.title,
    )
    db.commit()
    db.refresh(art)
    return art


def _collect_references(sections: list[dict]) -> list[dict]:
    seen: set[str] = set()
    refs: list[dict] = []
    for sec in sections:
        for c in sec.get("citations") or []:
            pid = c.get("paper_id") or ""
            key = pid or f"{c.get('title')}|{c.get('year')}"
            if not key or key in seen:
                continue
            seen.add(key)
            authors = c.get("authors") or []
            refs.append(
                {
                    "paper_id": pid,
                    "title": c.get("title") or "",
                    "authors": authors,
                    "year": c.get("year"),
                    "citation_ids": [c.get("citation_id")],
                }
            )
    return refs


def citation_check(db: Session, project: Project) -> ProjectArtifact:
    doc = latest_artifact(db, project.id, "document")
    if not doc:
        raise LookupError("尚无正文可核查")
    paragraphs: list[str] = []
    citations = []
    for sec in (doc.payload or {}).get("sections") or []:
        for p in sec.get("paragraphs") or []:
            paragraphs.append(p)
        for c in sec.get("citations") or []:
            cid = c.get("citation_id") or ""
            sentence = next(
                (p for p in sec.get("paragraphs") or [] if cid and cid in p),
                (sec.get("paragraphs") or [""])[0] if sec.get("paragraphs") else "",
            )
            # 正式引用：必须有库内论文 id、页码与证据片段；否则按非正式交 S9 检出
            is_formal = bool(c.get("paper_id") and c.get("snippet") and c.get("page_start"))
            citations.append(
                {
                    "sentence": sentence,
                    "paper_id": c.get("paper_id"),
                    "title": c.get("title"),
                    "authors": c.get("authors") or [],
                    "year": c.get("year"),
                    "page_start": c.get("page_start"),
                    "evidence_snippet": c.get("snippet"),
                    "is_formal": is_formal,
                }
            )
    if not paragraphs:
        paragraphs = ["（空正文）"]
    result = run_s9({"paragraphs": paragraphs, "citations": citations}, db=db)
    if result.status != "succeeded":
        raise RuntimeError(result.error or "引用核查失败")
    project.status = "checking" if not result.data.get("passed") else "exportable"
    return save_artifact(db, project, kind="citation_check", payload=result.data, title=project.title)


def export_document(
    db: Session,
    project: Project,
    *,
    mode: str = "draft",
) -> ProjectArtifact:
    doc = latest_artifact(db, project.id, "document")
    if not doc:
        raise LookupError("尚无正文可导出")
    check = latest_artifact(db, project.id, "citation_check")
    passed = bool((check.payload or {}).get("passed")) if check else False
    if mode == "final" and not passed:
        raise PermissionError("定稿导出被拒绝：引用核查未全部通过；可改为草稿导出")

    sections_raw = list((doc.payload or {}).get("sections") or [])
    sections_in = []
    for sec in sections_raw:
        sections_in.append({"title": sec.get("title") or "章节", "paragraphs": sec.get("paragraphs") or []})
    if not sections_in:
        sections_in = [{"title": "正文", "paragraphs": ["（空）"]}]

    references = _collect_references(sections_raw)
    out_dir = EXPORT_DIR / project.id
    result = run_s10(
        {
            "title": project.title,
            "author": "作者",
            "sections": sections_in,
            "references": references,
            "mode": mode,
            "citation_check_passed": passed,
            "output_dir": str(out_dir),
        }
    )
    if result.status != "succeeded":
        raise RuntimeError(result.error or "导出失败")
    if mode == "final":
        project.status = "exportable"
    return save_artifact(
        db,
        project,
        kind="export",
        payload={
            "mode": mode,
            "files": result.data,
            "citation_passed": passed,
            "references": references,
            "research_goal": _research_goal(project),
        },
        title=project.title,
    )
