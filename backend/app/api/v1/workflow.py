"""大纲 / 写作 / 润色 / 核查 / 导出 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.api.deps import current_user
from backend.app.db import get_db
from backend.app.models.user import Project, User
from backend.app.services import project_workflow as wf

router = APIRouter(prefix="/projects", tags=["workflow"])


def _owned(db: Session, user: User, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "项目不存在"})
    return project


def _art_view(art) -> dict:
    return {
        "id": art.id,
        "project_id": art.project_id,
        "kind": art.kind,
        "version": art.version,
        "title": art.title,
        "confirmed": art.confirmed,
        "payload": art.payload,
        "created_at": art.created_at.isoformat() if art.created_at else None,
    }


class OutlineBody(BaseModel):
    research_goal: str | None = None


class OutlineUpdateBody(BaseModel):
    nodes: list[dict] = Field(default_factory=list)
    topic_name: str | None = None
    paper_type: str | None = None


class SectionDraftBody(BaseModel):
    section_title: str = Field(min_length=1)
    writing_intent: str = ""


class BatchDraftBody(BaseModel):
    max_chapters: int = Field(default=8, ge=1, le=12)
    # missing：只写未写章节；all：重写全文（覆盖已写）
    mode: str = Field(default="missing", pattern="^(missing|all)$")


class DocumentBody(BaseModel):
    sections: list[dict] = Field(default_factory=list)


class PolishBody(BaseModel):
    level: str = "academic"
    user_request: str = ""
    text: str | None = None


class ExportBody(BaseModel):
    mode: str = "draft"  # draft | final


@router.post("/{project_id}/outlines")
def create_outline(
    project_id: str,
    body: OutlineBody,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _owned(db, user, project_id)
    try:
        art = wf.generate_outline(db, project, body.research_goal)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail={"code": "SKILL_FAILED", "message": str(exc)}) from exc
    return {"code": "OK", "message": "大纲已生成，待确认", "data": _art_view(art)}


@router.get("/{project_id}/outlines/latest")
def get_latest_outline(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = _owned(db, user, project_id)
    art = wf.latest_artifact(db, project.id, "outline")
    if not art:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "尚无大纲"})
    return {"code": "OK", "message": "ok", "data": _art_view(art)}


@router.put("/{project_id}/outlines")
def put_outline(
    project_id: str,
    body: OutlineUpdateBody,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """手工编辑大纲：另存新版本；若此前已确认则取消确认，需再次确认。"""
    project = _owned(db, user, project_id)
    try:
        art = wf.update_outline(
            db,
            project,
            nodes=body.nodes,
            topic_name=body.topic_name,
            paper_type=body.paper_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "OUTLINE_INVALID", "message": str(exc)}) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": str(exc)}) from exc
    return {"code": "OK", "message": "大纲已保存，请确认后再写作", "data": _art_view(art)}


@router.post("/{project_id}/outlines/{vid}/confirm")
def confirm_outline(
    project_id: str,
    vid: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _owned(db, user, project_id)
    try:
        version = int(vid) if str(vid).isdigit() else int(str(vid).lstrip("vV"))
        art = wf.confirm_outline_artifact(db, project, version)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": str(exc)}) from exc
    return {"code": "OK", "message": "大纲已确认", "data": _art_view(art)}


@router.get("/{project_id}/writing-plan")
def get_writing_plan(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = _owned(db, user, project_id)
    plan = wf.writing_plan(db, project)
    plan["next_step"] = wf.next_step(db, project)
    plan["flow_step"] = wf.flow_step_index(db, project)
    plan["flow_steps"] = [
        {"key": "search", "title": "检索文献"},
        {"key": "outline", "title": "确认大纲"},
        {"key": "editor", "title": "章节写作"},
        {"key": "polish", "title": "润色确认"},
        {"key": "citations", "title": "引用核查"},
        {"key": "export", "title": "导出成稿"},
    ]
    return {"code": "OK", "message": "ok", "data": plan}


@router.post("/{project_id}/sections/{sid}/drafts")
def draft_section(
    project_id: str,
    sid: str,
    body: SectionDraftBody,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _owned(db, user, project_id)
    # sid 可为大纲节点 id；只替换这一节，其它章节保留
    plan = wf.writing_plan(db, project)
    matched = next((c for c in plan["chapters"] if c.get("id") == sid or c.get("title") == body.section_title), None)
    title = body.section_title or (matched["title"] if matched else "")
    intent = body.writing_intent or (matched.get("intent") if matched else "")
    section_id = (matched or {}).get("id") or (sid if sid and sid != "main" else "")
    try:
        art = wf.write_section(
            db,
            project,
            section_title=title,
            writing_intent=intent or "",
            related_paper_ids=(matched or {}).get("related_paper_ids") or [],
            section_id=section_id or None,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=400, detail={"code": "OUTLINE_NOT_CONFIRMED", "message": str(exc)}
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail={"code": "SKILL_FAILED", "message": str(exc)}) from exc
    return {"code": "OK", "message": "本节已生成/重写，其它章节未改动", "data": _art_view(art)}


@router.post("/{project_id}/sections/batch-drafts")
def batch_draft_sections(
    project_id: str,
    body: BatchDraftBody,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _owned(db, user, project_id)
    try:
        if body.mode == "all":
            art = wf.rewrite_all_chapters(db, project, max_chapters=body.max_chapters)
        else:
            art = wf.write_missing_chapters(db, project, max_chapters=body.max_chapters)
    except PermissionError as exc:
        raise HTTPException(
            status_code=400, detail={"code": "OUTLINE_NOT_CONFIRMED", "message": str(exc)}
        ) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail={"code": "SKILL_FAILED", "message": str(exc)}) from exc
    msg = "全文已按大纲重写" if body.mode == "all" else "已按大纲生成缺失章节"
    return {"code": "OK", "message": msg, "data": _art_view(art)}


@router.get("/{project_id}/document")
def get_document(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = _owned(db, user, project_id)
    art = wf.latest_artifact(db, project.id, "document")
    if not art:
        return {"code": "OK", "message": "ok", "data": None}
    return {"code": "OK", "message": "ok", "data": _art_view(art)}


@router.put("/{project_id}/document")
def put_document(
    project_id: str,
    body: DocumentBody,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _owned(db, user, project_id)
    art = wf.save_document(db, project, body.sections)
    return {"code": "OK", "message": "正文已保存", "data": _art_view(art)}


@router.post("/{project_id}/polishes")
def create_polish(
    project_id: str,
    body: PolishBody,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _owned(db, user, project_id)
    try:
        art = wf.polish_document(
            db, project, level=body.level, user_request=body.user_request, text=body.text
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail={"code": "SKILL_FAILED", "message": str(exc)}) from exc
    return {"code": "OK", "message": "润色结果待确认", "data": _art_view(art)}


@router.get("/{project_id}/polishes/latest")
def latest_polish(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = _owned(db, user, project_id)
    art = wf.latest_artifact(db, project.id, "polish")
    if not art:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "尚无润色记录"})
    return {"code": "OK", "message": "ok", "data": _art_view(art)}


@router.post("/{project_id}/polishes/{pid}/confirm")
def confirm_polish(
    project_id: str,
    pid: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _owned(db, user, project_id)
    try:
        # pid 可为 artifact id 或 version
        art = wf.latest_artifact(db, project.id, "polish")
        if not art:
            raise LookupError("尚无润色记录")
        if art.id != pid and str(art.version) != str(pid):
            # 按 version 精确确认
            version = int(pid) if str(pid).isdigit() else art.version
            art = wf.confirm_polish(db, project, version)
        else:
            art = wf.confirm_polish(db, project, art.version)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail={"code": "FORBIDDEN", "message": str(exc)}) from exc
    return {"code": "OK", "message": "润色已确认并写入正文", "data": _art_view(art)}


@router.post("/{project_id}/citation-checks")
def run_citation_check(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = _owned(db, user, project_id)
    try:
        art = wf.citation_check(db, project)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail={"code": "SKILL_FAILED", "message": str(exc)}) from exc
    return {"code": "OK", "message": "核查完成", "data": _art_view(art)}


@router.get("/{project_id}/citation-checks/latest")
def latest_citation_check(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = _owned(db, user, project_id)
    art = wf.latest_artifact(db, project.id, "citation_check")
    if not art:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "尚无核查记录"})
    return {"code": "OK", "message": "ok", "data": _art_view(art)}


@router.post("/{project_id}/exports")
def create_export(
    project_id: str,
    body: ExportBody,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _owned(db, user, project_id)
    try:
        art = wf.export_document(db, project, mode=body.mode)
    except PermissionError as exc:
        raise HTTPException(
            status_code=400, detail={"code": "CITATION_GATE_FAILED", "message": str(exc)}
        ) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400, detail={"code": "EXPORT_CONVERSION_FAILED", "message": str(exc)}
        ) from exc
    return {"code": "OK", "message": "导出成功", "data": _art_view(art)}


@router.get("/{project_id}/exports/latest")
def latest_export(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = _owned(db, user, project_id)
    art = wf.latest_artifact(db, project.id, "export")
    if not art:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "尚无导出"})
    return {"code": "OK", "message": "ok", "data": _art_view(art)}


@router.get("/{project_id}/exports/download")
def download_export(
    project_id: str,
    fmt: str = "docx",
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _owned(db, user, project_id)
    art = wf.latest_artifact(db, project.id, "export")
    if not art:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "尚无导出"})
    files = (art.payload or {}).get("files") or {}
    key = {"docx": "docx_path", "pdf": "pdf_path", "md": "markdown_path"}.get(fmt)
    if not key or not files.get(key):
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "文件不存在"})
    path = files[key]
    return FileResponse(path, filename=f"{project.title}.{fmt}")
