"""文本型 PDF 解析：正文、页码、粗粒度章节树。"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf as fitz


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


HEADING_RE = re.compile(
    r"^\s*((第[一二三四五六七八九十百零〇\d]+[章节部篇]|[一二三四五六七八九十]+、|\d+(\.\d+){0,2}\s+|[（(][一二三四五六七八九十\d]+[）)]).{0,40})$"
)

JUNK_TITLE_RE = re.compile(
    r"(第\d+期|总第|China|Film|Television|Journal|学报|月刊|周刊|DOI|作者简介|内容摘要|摘要|关键词|REVIEWS|FORUM|NEWS|THE FILM|DIANYING|XUESHU|FENGGE)",
    re.I,
)


@dataclass
class SectionNode:
    title: str
    page_start: int
    page_end: int | None = None
    children: list["SectionNode"] = field(default_factory=list)


@dataclass
class ParsedPage:
    page_no: int
    text: str


@dataclass
class ParseResult:
    title: str
    authors: list[str]
    abstract: str
    year: int | None
    page_count: int
    pages: list[ParsedPage]
    section_tree: list[SectionNode]
    section_recognized: bool
    full_text: str


def _looks_like_title(text: str) -> bool:
    t = text.strip()
    if not (6 <= len(t) <= 80):
        return False
    if JUNK_TITLE_RE.search(t):
        return False
    if re.fullmatch(r"[\d\W_]+", t):
        return False
    # 中文题名通常含汉字
    if re.search(r"[\u4e00-\u9fff]", t):
        return True
    # 英文题名至少两个单词且不全大写缩写
    words = t.split()
    return len(words) >= 2 and not t.isupper()


def _guess_title(doc: fitz.Document, first_page_text: str, fallback: str = "未识别题名") -> str:
    meta_title = ((doc.metadata or {}).get("title") or "").strip()
    if meta_title and _looks_like_title(meta_title):
        return meta_title
    for line in first_page_text.splitlines():
        line = line.strip()
        if _looks_like_title(line):
            return line
    if fallback and fallback != "未识别题名":
        return fallback
    return "未识别题名"


def _guess_year(text: str) -> int | None:
    years = re.findall(r"(19|20)\d{2}", text[:3000])
    if not years:
        return None
    # years is like ['20','20'] from groups; fix
    full = re.findall(r"(?:19|20)\d{2}", text[:3000])
    if not full:
        return None
    vals = [int(y) for y in full if 1980 <= int(y) <= 2035]
    return vals[0] if vals else None


def _guess_authors(first_page_text: str) -> list[str]:
    lines = [ln.strip() for ln in first_page_text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return []
    candidate = lines[1]
    if len(candidate) <= 40 and not HEADING_RE.match(candidate):
        parts = re.split(r"[，,、/\s]+", candidate)
        names = [p for p in parts if 1 < len(p) <= 12]
        return names[:6]
    return []


def _guess_abstract(text: str) -> str:
    m = re.search(r"(摘要|Abstract)[:：\s]*(.+?)(关键词|Key\s*words|引言|一、|1\s)", text, re.S | re.I)
    if not m:
        return ""
    abstract = re.sub(r"\s+", " ", m.group(2)).strip()
    return abstract[:800]


def _build_sections(pages: list[ParsedPage]) -> tuple[list[SectionNode], bool]:
    nodes: list[SectionNode] = []
    for page in pages:
        for line in page.text.splitlines():
            line = line.strip()
            if not line or len(line) > 60:
                continue
            if HEADING_RE.match(line):
                if nodes:
                    nodes[-1].page_end = page.page_no
                nodes.append(SectionNode(title=line, page_start=page.page_no))
    if nodes:
        nodes[-1].page_end = pages[-1].page_no if pages else nodes[-1].page_start
        return nodes, True
    return [], False


def title_from_filename(name: str) -> str:
    stem = Path(name).stem
    if "_" in stem:
        return stem.rsplit("_", 1)[0].replace("_", "")
    return stem


def parse_pdf(path: Path) -> ParseResult:
    doc = fitz.open(path)
    try:
        pages: list[ParsedPage] = []
        for i in range(doc.page_count):
            page = doc.load_page(i)
            text = page.get_text("text") or ""
            pages.append(ParsedPage(page_no=i + 1, text=text))
        full_text = "\n".join(p.text for p in pages)
        first = pages[0].text if pages else ""
        section_tree, recognized = _build_sections(pages)
        fallback = title_from_filename(path.name)
        return ParseResult(
            title=_guess_title(doc, first, fallback=fallback),
            authors=_guess_authors(first),
            abstract=_guess_abstract(full_text),
            year=_guess_year(full_text),
            page_count=doc.page_count,
            pages=pages,
            section_tree=section_tree,
            section_recognized=recognized,
            full_text=full_text,
        )
    finally:
        doc.close()


def chunk_pages(
    pages: list[ParsedPage],
    *,
    target_chars: int = 800,
    overlap_chars: int = 120,
) -> list[dict]:
    chunks: list[dict] = []
    buf = ""
    page_start = pages[0].page_no if pages else 1
    page_end = page_start
    index = 0

    def flush():
        nonlocal buf, page_start, page_end, index
        text = buf.strip()
        if not text:
            return
        chunks.append(
            {
                "chunk_index": index,
                "page_start": page_start,
                "page_end": page_end,
                "content": text,
            }
        )
        index += 1
        if overlap_chars > 0 and len(text) > overlap_chars:
            buf = text[-overlap_chars:]
        else:
            buf = ""
        page_start = page_end

    for page in pages:
        page_end = page.page_no
        for paragraph in re.split(r"\n{2,}", page.text):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if len(buf) + len(paragraph) + 1 <= target_chars:
                buf = f"{buf}\n{paragraph}".strip()
            else:
                flush()
                buf = paragraph
                page_start = page.page_no
                page_end = page.page_no
    flush()
    return chunks
