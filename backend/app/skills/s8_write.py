"""S8 章节写作：大纲已确认后生成正文；正式引用必须回链库内论文与证据片段。

写作要求：
- 按「提出问题 → 分述证据 → 综合小结」组织，禁止把检索片段无逻辑堆砌。
- 有对话模型时：在证据约束下生成连贯论述。
- 无对话模型时：用结构化模板组织证据，仍保持学术衔接，不编造库外文献。
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from backend.app.adapters.chat import ChatNotConfigured, get_chat_adapter
from backend.app.db import SessionLocal
from sqlalchemy import select

from backend.app.models import KnowledgeChunk, Paper
from backend.app.skills.base import SkillRequest, SkillResult
from backend.app.skills.s2_retrieve import keyword_search, run_s2

DRAFT_NO_EVIDENCE = "无证据草稿"


class S8Input(BaseModel):
    section_title: str
    writing_intent: str = ""
    outline_confirmed: bool = False
    research_goal: str = ""
    prior_sections_summary: str = ""
    related_paper_ids: list[str] = Field(default_factory=list)
    exclude_paper_ids: list[str] = Field(default_factory=list)
    section_role: str = "body"  # intro | body | method | conclusion
    max_evidence: int = Field(default=5, ge=1, le=8)
    # single_section：只写本节，禁止扩写成整篇
    write_scope: str = "single_section"


class CitationOut(BaseModel):
    citation_id: str
    paper_id: str
    title: str
    authors: list[str]
    year: int | None
    page_start: int
    page_end: int
    snippet: str
    support_level: str  # 支持 | 部分支持 | 未找到证据


class ParagraphOut(BaseModel):
    text: str
    citation_ids: list[str] = Field(default_factory=list)
    is_formal: bool = True
    note: str | None = None


class S8Output(BaseModel):
    section_title: str
    paragraphs: list[ParagraphOut]
    citations: list[CitationOut]
    writer: str = "template"  # template | llm


_HEADER_NOISE = re.compile(
    r"("
    r"总第\s*\d+\s*期|第\s*\d+\s*期|"
    r"\d{4}\s*年\s*第?\s*\d+\s*期|"
    r"DOI[:：]?[\w．.／/\-]+|"
    r"【作者简介】[\s\S]{0,220}?。"
    r"|作者简介[:：][\s\S]{0,220}?。"
    r"|责任编辑[:：]\s*\S{1,20}"
    r"|[\[［]\s*摘\s*要\s*[\]］]|摘\s*要\s*[:：]"
    r"|关键词\s*[:：][^。]{0,100}"
    r"|中图分类号\s*[:：]\S+"
    r"|文献标识码\s*[:：]\S+"
    r"|Film Theory|MOVIE REVIEW|DEVELOPMENT RESEARCH|学术论坛|电影\s*评介"
    r"|\d{2,4}\s*影视现状研究"
    r"|[（(]\s*[^）)]{0,48}(?:大学|学院|研究所)[^）)]{0,48}[）)]"
    r"|女，[^，,]{2,12}人，"
    r"|主要从事[^。]{2,48}"
    r")",
    re.I,
)


def _is_usable_sentence(s: str, *, title: str = "") -> bool:
    s = s.strip()
    if len(s) < 20:
        return False
    hans = len(re.findall(r"[\u4e00-\u9fff]", s))
    if hans < 16:
        return False
    bad = (
        "作者简介",
        "责任编辑",
        "关键词",
        "中图分类号",
        "文献标识码",
        "基金项目",
        "摘 要",
        "参考文献",
        "青年记者",
        "电影文学",
        "广电视听",
        "HOT TOPIC",
        "学术论坛",
    )
    if any(b in s for b in bad):
        return False
    # 刊头/页码碎片
    if re.match(r"^[\d\sA-Za-z·.．/第期总]+", s) and hans < 28:
        return False
    if title and title[:10] in s and hans < 40:
        return False
    if "。" not in s and "，" not in s and "、" not in s:
        return False
    # 论断性：至少像在陈述而非目录
    if hans / max(len(s), 1) < 0.55:
        return False
    return True


def _clean_snippet(text: str, limit: int = 100, *, title: str = "", authors: list[str] | None = None) -> str:
    """从切片/摘要中抽出可用于论述的句子，去掉刊名页眉与作者简介。"""
    raw = re.sub(r"\s+", " ", (text or "")).strip()
    if not raw:
        return ""

    # 优先截取「摘要」之后
    m = re.search(r"[\[［]?\s*摘\s*要\s*[\]］]?\s*[:：]?", raw)
    if m:
        raw = raw[m.end() :]

    # 作者简介之后的正文往往更干净
    for bio in ("【作者简介】", "作者简介：", "作者简介:"):
        if bio in raw:
            after = raw.split(bio, 1)[1]
            # 跳过到第一个句号后
            cut = after.find("。")
            if cut >= 0:
                raw = after[cut + 1 :]

    raw = _HEADER_NOISE.sub(" ", raw)
    # 刊名拼音、年份栏目残留
    raw = re.sub(r"[A-Za-z]{2,}(?:\s*/\s*|\s+)", " ", raw)
    raw = re.sub(r"/?\s*\d{4}\s*年\s*/?", " ", raw)
    raw = re.sub(r"总第\s*\d+\s*期", " ", raw)
    # 去掉题名、作者名的重复出现
    if title:
        raw = raw.replace(title, " ")
    for a in authors or []:
        if a and len(a) >= 2:
            raw = raw.replace(a, " ")
    raw = re.sub(r"\s+", " ", raw).strip(" ，,;；/|")
    # 从首个汉字起截取，丢掉前缀噪音
    m_cn = re.search(r"[\u4e00-\u9fff]", raw)
    if m_cn:
        raw = raw[m_cn.start() :]

    parts = re.split(r"(?<=[。！？；])", raw)
    chosen: list[str] = []
    for part in parts:
        part = part.strip()
        if not part.endswith(("。", "！", "？", "；")):
            part = part + "。" if len(part) >= 20 else part
        if not _is_usable_sentence(part, title=title):
            continue
        chosen.append(part if part.endswith(("。", "！", "？")) else part + "。")
        if len("".join(chosen)) >= 48:
            break
    if not chosen:
        return ""

    out = "".join(chosen)
    # 去掉 OCR 造成的汉字间多余空格
    out = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", out)
    if len(out) > limit + 30:
        cut = out[: limit + 30].rfind("。")
        if cut >= 24:
            out = out[: cut + 1]
        else:
            out = out[:limit] + "…"
    return out



def _cite_label(authors: list[str], year: int | None) -> str:
    if authors:
        name = authors[0]
        if len(authors) > 1:
            name = f"{authors[0]}等"
    else:
        name = "有关研究"
    y = str(year) if year else "年份未识别"
    return f"{name}（{y}）"


def _gather_hits(db: Session, title: str, intent: str, goal: str, max_evidence: int):
    query = " ".join(x for x in [title, intent, goal] if x).strip() or title
    # 优先混合检索；失败则关键词
    hybrid = run_s2(
        {"query": query, "language": "zh", "top_k": max_evidence, "mode": "hybrid"},
        db=db,
    )
    if hybrid.status == "succeeded" and hybrid.data.get("papers"):
        return hybrid.data["papers"], "hybrid"
    hits = keyword_search(db, query, top_k=max_evidence)
    return [h.model_dump() for h in hits], "keyword"


def _pick_evidence_text(
    db: Session,
    paper: Paper | None,
    hit: dict,
) -> tuple[str, int, int]:
    """选一条可写入论述的证据句，并返回对应页码。"""
    title = (paper.title if paper else hit.get("title")) or ""
    authors = list(hit.get("authors") or (paper.authors if paper else []) or [])
    page_start = int(hit.get("page_start") or 1)
    page_end = int(hit.get("page_end") or page_start)

    candidates: list[tuple[str, int, int]] = [
        (hit.get("snippet") or "", page_start, page_end),
        ((paper.abstract if paper else "") or "", page_start, page_end),
    ]
    if paper:
        chunks = list(
            db.scalars(
                select(KnowledgeChunk)
                .where(KnowledgeChunk.paper_id == paper.id)
                .order_by(KnowledgeChunk.chunk_index.asc())
                .limit(8)
            ).all()
        )
        for ch in chunks:
            candidates.append(
                (ch.content or "", int(ch.page_start or 1), int(ch.page_end or ch.page_start or 1))
            )

    for text, ps, pe in candidates:
        cleaned = _clean_snippet(text, title=title, authors=authors)
        if cleaned:
            return cleaned, ps, pe
    return "", page_start, page_end


def _build_citations(db: Session, hits: list[dict]) -> list[CitationOut]:
    """只从公用库已索引论文建正式引用；元数据以库内为准。"""
    citations: list[CitationOut] = []
    for hit in hits:
        paper = db.get(Paper, hit["paper_id"])
        if not paper or paper.status != "indexed" or not paper.is_public:
            continue
        snippet, page_start, page_end = _pick_evidence_text(db, paper, hit)
        if not snippet or page_start < 1:
            continue
        citations.append(
            CitationOut(
                citation_id=f"C{len(citations) + 1}",
                paper_id=paper.id,
                title=paper.title,
                authors=list(paper.authors or []),
                year=paper.publication_year,
                page_start=page_start,
                page_end=page_end,
                snippet=snippet,
                support_level="支持" if float(hit.get("score") or 0) >= 2 else "部分支持",
            )
        )
    return citations


# 产品硬约束：管理端可改风格提示词，但不能绕过「只许用给定证据 id」
_CITATION_GATE = (
    "【引用硬约束，不可违反】只能使用 evidence 列表中的 id（如 C1）做正式引用；"
    "禁止编造库外题名、作者、年份或页码；禁止输出不在 evidence 中的引用编号；"
    "证据不足的句子不要加引用编号，也不要写成定论。"
)

_SECTION_SCOPE_GATE = (
    "【章节范围硬约束】本次只写 section_title 对应的这一节，不要写其他章节标题，"
    "不要输出绪论到结论的整篇结构，不要把后文章节内容提前写进本节。"
)


def _sanitize_paragraphs(
    paragraphs: list[ParagraphOut],
    allowed: dict[str, CitationOut],
) -> list[ParagraphOut]:
    """清洗模型输出：删除库外引用编号；曾声称引用但洗净后无库内 id 的句子标无证据草稿。"""
    out: list[ParagraphOut] = []
    for p in paragraphs:
        raw_text = str(p.text or "").strip()
        if not raw_text:
            continue
        claimed_ids = set(p.citation_ids or []) | set(re.findall(r"\[(C\d+)\]", raw_text))
        had_citation_claim = bool(claimed_ids) or (p.note == DRAFT_NO_EVIDENCE)

        def _keep_mark(mo: re.Match) -> str:
            cid = mo.group(1)
            return mo.group(0) if cid in allowed else ""

        text = re.sub(r"\[(C\d+)\]", _keep_mark, raw_text)
        text = re.sub(r"\s{2,}", " ", text).strip()
        ids = [x for x in (p.citation_ids or []) if x in allowed]
        for cid in re.findall(r"\[(C\d+)\]", text):
            if cid in allowed and cid not in ids:
                ids.append(cid)

        note = p.note
        if ids:
            is_formal = True
            if note == DRAFT_NO_EVIDENCE:
                note = None
            text = text.replace(f"（{DRAFT_NO_EVIDENCE}）", "").replace(DRAFT_NO_EVIDENCE, "").strip()
        elif had_citation_claim:
            # 声称有引用但无法回链到库内证据
            is_formal = False
            note = DRAFT_NO_EVIDENCE
            if DRAFT_NO_EVIDENCE not in text:
                text = f"{text}（{DRAFT_NO_EVIDENCE}）" if text else DRAFT_NO_EVIDENCE
        else:
            # 衔接段/问题提出段：允许无引用编号，但不作为正式引用句
            is_formal = False
            note = p.note
        out.append(
            ParagraphOut(
                text=text,
                citation_ids=ids,
                is_formal=is_formal,
                note=note,
            )
        )
    return out


def _retain_used_citations(
    paragraphs: list[ParagraphOut],
    citations: list[CitationOut],
) -> list[CitationOut]:
    used: set[str] = set()
    for p in paragraphs:
        used.update(p.citation_ids or [])
        for cid in re.findall(r"\[(C\d+)\]", p.text or ""):
            used.add(cid)
    return [c for c in citations if c.citation_id in used]


def _compact_intent(intent: str, goal: str) -> str:
    """去掉大纲模板里的『围绕主题…覆盖…』复读，只保留可写进正文的意图。"""
    t = (intent or "").strip()
    if not t:
        return "梳理相关研究现状并归纳可延伸的问题"
    t = re.sub(r"；?\s*围绕主题「[^」]+」展开", "", t)
    t = re.sub(r"；?\s*覆盖：.*$", "", t)
    if goal:
        t = t.replace(goal, "本文研究对象")
    t = re.sub(r"\s+", " ", t).strip(" ；;")
    return t or "梳理相关研究现状并归纳可延伸的问题"


def _compose_template(
    title: str,
    intent: str,
    goal: str,
    citations: list[CitationOut],
    *,
    prior: str = "",
    role: str = "body",
) -> list[ParagraphOut]:
    """无 LLM 时的结构化写作：问题—分述—小结，并衔接前文。"""
    paragraphs: list[ParagraphOut] = []
    goal_bit = goal or title
    intent_bit = _compact_intent(intent, goal_bit)

    if role == "intro":
        open_text = (
            f"本文围绕「{goal_bit}」展开。{intent_bit}。"
            f"本章先界定问题边界与论述范围，后续章节再依据公用知识库证据展开分析。"
        )
    elif role == "conclusion":
        open_text = (
            f"在前文讨论基础上，本章回扣「{goal_bit}」，{intent_bit}。"
            + (f"已有章节要点可概括为：{prior}" if prior else "论述仍严格限于库内可核对证据。")
        )
    elif role == "method":
        open_text = (
            f"针对「{goal_bit}」，本章说明分析路径与材料组织方式。{intent_bit}。"
            + (f"此前已交代：{prior}" if prior else "")
        )
    else:
        bridge = f"承接前文（{prior}），" if prior else ""
        open_text = (
            f"{bridge}围绕「{title}」，本节以「{goal_bit}」为问题边界，{intent_bit}。"
            f"论述仅依据公用知识库中已索引文献及其页码证据展开，证据不足处不强行定论。"
        )
    paragraphs.append(ParagraphOut(text=open_text.strip(), citation_ids=[], is_formal=True))

    if not citations:
        paragraphs.append(
            ParagraphOut(
                text=f"关于「{title}」，当前公用知识库证据不足，无法形成带正式引用的论述。",
                citation_ids=[],
                is_formal=False,
                note=DRAFT_NO_EVIDENCE,
            )
        )
        return paragraphs

    if role == "conclusion":
        transitions = [
            "回看既有研究可以发现",
            "与前述分析相呼应",
            "综合库内材料还可看到",
        ]
    elif role == "intro":
        transitions = [
            "既有讨论首先提示了问题的现实与学术背景",
            "在对象界定上，相关文献进一步指出",
            "由此也引出本文需要回应的关键争议",
        ]
    else:
        transitions = [
            "既有研究首先从问题提出与对象界定入手",
            "在此基础上，另有研究从材料与方法层面推进讨论",
            "同时，也有文献从语境、接受或比较视角补充观察",
            "此外，部分研究开始触及既有结论的适用边界",
            "最后，相关讨论也提示了现有论述仍待澄清之处",
        ]

    i = 0
    while i < len(citations):
        group = citations[i : i + 2]
        lead = transitions[min(i // 2, len(transitions) - 1)]
        bits: list[str] = []
        ids: list[str] = []
        for c in group:
            label = _cite_label(c.authors, c.year)
            claim = c.snippet.rstrip("。") + "。"
            bits.append(f"{label}认为，{claim}[{c.citation_id}]")
            ids.append(c.citation_id)
        if len(bits) == 1:
            body = f"{lead}。{bits[0]}"
        else:
            body = f"{lead}。{bits[0]}进一步看，{bits[1]}"
        paragraphs.append(ParagraphOut(text=body, citation_ids=ids, is_formal=True))
        i += 2

    marks = "".join(f"[{c.citation_id}]" for c in citations)
    if role == "conclusion":
        close = (
            f"综上，围绕「{goal_bit}」可归纳出若干可核对结论，主要依据见{marks}。"
            f"上述判断均来自库内证据；库内未覆盖之处应明确标为研究局限，而不宜上升为全局定论。"
        )
    else:
        close = (
            f"综合以上材料可见，围绕「{title}」的讨论已形成若干可核对的线索，主要依据见{marks}。"
            f"这些证据能够支撑本节的问题意识，但仍需在后续章节中比较不同取径的差异，"
            f"并明确指出库内尚未充分覆盖的方面，以免把局部观察上升为全局定论。"
        )
    paragraphs.append(
        ParagraphOut(
            text=close,
            citation_ids=[c.citation_id for c in citations],
            is_formal=True,
        )
    )
    return paragraphs


def _compose_with_llm(
    title: str,
    intent: str,
    goal: str,
    citations: list[CitationOut],
    *,
    prior: str = "",
    role: str = "body",
    system_prompt: str = "",
) -> list[ParagraphOut] | None:
    adapter = get_chat_adapter()
    if not adapter.available():
        return None
    evidence = [
        {
            "id": c.citation_id,
            "authors": c.authors,
            "year": c.year,
            "title": c.title,
            "page": c.page_start,
            "snippet": c.snippet,
        }
        for c in citations
    ]
    system = (system_prompt or "").strip()
    if not system:
        return None
    # 管理端提示词之后追加硬约束，防止改提示词绕过引用闸门或写成整篇
    system = f"{system}\n{_CITATION_GATE}\n{_SECTION_SCOPE_GATE}"
    user = {
        "section_title": title,
        "writing_intent": intent,
        "research_goal": goal,
        "section_role": role,
        "write_scope": "single_section",
        "prior_sections_summary": prior,
        "evidence": evidence,
        "allowed_citation_ids": [c.citation_id for c in citations],
        "instruction": "只生成本节正文段落，禁止输出其他章节。",
    }
    try:
        raw = adapter.chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            temperature=0.2,
            max_tokens=1600,
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
    allowed_map = {c.citation_id: c for c in citations}
    draft: list[ParagraphOut] = []
    for p in data.get("paragraphs") or []:
        text = str(p.get("text") or "").strip()
        if not text:
            continue
        ids = [x for x in (p.get("citation_ids") or []) if x in allowed_map]
        draft.append(ParagraphOut(text=text, citation_ids=ids, is_formal=True))
    cleaned = _sanitize_paragraphs(draft, allowed_map)
    return cleaned or None


def _prefer_related_hits(
    db: Session,
    related_ids: list[str],
    hits: list[dict],
    max_evidence: int,
    *,
    exclude_ids: list[str] | None = None,
) -> list[dict]:
    exclude = set(exclude_ids or [])
    preferred: list[dict] = []
    rest: list[dict] = []
    related_set = set(related_ids or [])
    for h in hits:
        pid = h.get("paper_id")
        if not pid or pid in exclude:
            continue
        (preferred if pid in related_set else rest).append(h)
    have = {h.get("paper_id") for h in preferred}
    for pid in related_ids or []:
        if pid in have or pid in exclude:
            continue
        paper = db.get(Paper, pid)
        if not paper or paper.status != "indexed":
            continue
        ch = db.scalars(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.paper_id == paper.id)
            .order_by(KnowledgeChunk.chunk_index.asc())
            .limit(1)
        ).first()
        preferred.append(
            {
                "paper_id": paper.id,
                "title": paper.title,
                "authors": list(paper.authors or []),
                "year": paper.publication_year,
                "snippet": (ch.content if ch else (paper.abstract or paper.title or ""))[:240],
                "page_start": int(ch.page_start) if ch and ch.page_start else 1,
                "page_end": int(ch.page_end or ch.page_start) if ch else 1,
                "score": 3.0,
            }
        )
        have.add(pid)
    # 若排除后不足，再允许使用已用文献（避免整节无证据）
    fallback = [h for h in hits if h.get("paper_id") and h.get("paper_id") not in have]
    merged = preferred + rest + fallback
    seen: set[str] = set()
    out: list[dict] = []
    for h in merged:
        pid = h.get("paper_id")
        if not pid or pid in seen:
            continue
        seen.add(pid)
        out.append(h)
        if len(out) >= max_evidence:
            break
    return out


def _write_with_evidence(
    db: Session,
    title: str,
    intent: str,
    goal: str,
    max_evidence: int,
    *,
    prior: str = "",
    role: str = "body",
    related_paper_ids: list[str] | None = None,
    exclude_paper_ids: list[str] | None = None,
) -> S8Output:
    hits, _channel = _gather_hits(db, title, intent, goal, max(max_evidence + 4, 8))
    hits = _prefer_related_hits(
        db,
        related_paper_ids or [],
        hits,
        max_evidence,
        exclude_ids=exclude_paper_ids,
    )
    citations = _build_citations(db, hits)
    writer = "template"
    from backend.app.services.llm_settings import get_active_prompt

    system_prompt = get_active_prompt(db, "S8", "system")
    paragraphs = _compose_with_llm(
        title,
        intent,
        goal,
        citations,
        prior=prior,
        role=role,
        system_prompt=system_prompt,
    )
    if paragraphs is None:
        paragraphs = _compose_template(title, intent, goal, citations, prior=prior, role=role)
    else:
        writer = "llm"
    allowed_map = {c.citation_id: c for c in citations}
    paragraphs = _sanitize_paragraphs(paragraphs, allowed_map)
    citations = _retain_used_citations(paragraphs, citations)
    # 二次闸门：正式引用必须仍指向已索引论文
    safe_citations: list[CitationOut] = []
    for c in citations:
        paper = db.get(Paper, c.paper_id)
        if paper and paper.status == "indexed" and paper.is_public and c.snippet and c.page_start >= 1:
            safe_citations.append(c)
    allowed_ids = {c.citation_id for c in safe_citations}
    paragraphs = _sanitize_paragraphs(
        [
            ParagraphOut(
                text=p.text,
                citation_ids=[x for x in (p.citation_ids or []) if x in allowed_ids],
                is_formal=p.is_formal,
                note=p.note,
            )
            for p in paragraphs
        ],
        {c.citation_id: c for c in safe_citations},
    )
    return S8Output(
        section_title=title,
        paragraphs=paragraphs,
        citations=safe_citations,
        writer=writer,
    )


def run_s8(req: SkillRequest | dict[str, Any], db: Session | None = None) -> SkillResult:
    started = time.perf_counter()
    if isinstance(req, dict):
        req = SkillRequest(skill_code="S8", input=req)
    try:
        payload = S8Input.model_validate(req.input)
    except ValidationError as exc:
        return SkillResult(
            skill_code="S8",
            status="failed",
            error=f"输入校验失败: {exc}",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    if not payload.outline_confirmed:
        return SkillResult(
            skill_code="S8",
            status="failed",
            error="大纲未确认，不能批量生成章节；仅允许确认后的章节写作",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    owns = db is None
    session = db or SessionLocal()
    try:
        out = _write_with_evidence(
            session,
            payload.section_title,
            payload.writing_intent,
            payload.research_goal,
            payload.max_evidence,
            prior=payload.prior_sections_summary,
            role=payload.section_role or "body",
            related_paper_ids=payload.related_paper_ids,
            exclude_paper_ids=payload.exclude_paper_ids,
        )
        for c in out.citations:
            paper = session.get(Paper, c.paper_id)
            assert paper and paper.status == "indexed"
            assert c.page_start >= 1 and c.snippet
        return SkillResult(
            skill_code="S8",
            status="succeeded",
            data=out.model_dump(),
            evidence_refs=[
                {
                    "citation_id": c.citation_id,
                    "paper_id": c.paper_id,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                }
                for c in out.citations
            ],
            model_id=get_chat_adapter().model_id if out.writer == "llm" else "template-s8",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        return SkillResult(
            skill_code="S8",
            status="failed",
            error=str(exc),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    finally:
        if owns:
            session.close()
