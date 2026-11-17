#!/usr/bin/env python3
"""扫描 `论文/` 并增量入库公用知识库。

用法：
  python scripts/sync_corpus.py
  python scripts/sync_corpus.py --dry-run
  python scripts/sync_corpus.py --reparse 论文/某文件.pdf
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.services.pdf_parser import (  # noqa: E402
    chunk_pages,
    parse_pdf,
    title_from_filename,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def list_pdfs(papers_dir: Path) -> list[Path]:
    return sorted(p for p in papers_dir.rglob("*.pdf") if p.is_file())


def process_one(
    pdf: Path,
    *,
    root: Path,
    storage_dir: Path,
    papers_dir: Path,
    config: dict,
    force: bool,
) -> dict:
    rel = str(pdf.relative_to(root)) if pdf.is_relative_to(root) else str(pdf)
    size = pdf.stat().st_size
    max_bytes = int(config.get("corpus", {}).get("max_file_mb", 30)) * 1024 * 1024
    if size > max_bytes:
        return {
            "path": rel,
            "status": "failed",
            "error": f"超过 {max_bytes // (1024 * 1024)} MB",
        }

    digest = sha256_file(pdf)
    paper_id = digest[:32]
    paper_dir = storage_dir / "papers" / paper_id
    meta_path = paper_dir / "meta.json"

    if meta_path.exists() and not force:
        meta = load_json(meta_path, {})
        if meta.get("status") == "indexed" and meta.get("sha256") == digest:
            return {
                "path": rel,
                "paper_id": paper_id,
                "sha256": digest,
                "status": "skipped",
                "title": meta.get("title"),
            }

    try:
        parsed = parse_pdf(pdf)
    except Exception as exc:  # noqa: BLE001
        return {
            "path": rel,
            "sha256": digest,
            "status": "failed",
            "error": f"解析失败: {exc}",
        }

    if not parsed.full_text.strip():
        return {
            "path": rel,
            "sha256": digest,
            "status": "failed",
            "error": "未提取到文本，可能是扫描件或加密 PDF",
        }

    chunk_cfg = config.get("chunking", {})
    chunks = chunk_pages(
        parsed.pages,
        target_chars=int(chunk_cfg.get("target_chars", 800)),
        overlap_chars=int(chunk_cfg.get("overlap_chars", 120)),
    )

    paper_dir.mkdir(parents=True, exist_ok=True)
    stored_pdf = paper_dir / "source.pdf"
    if not stored_pdf.exists() or force:
        shutil.copy2(pdf, stored_pdf)

    # 预置包文件名多为「题名_作者.pdf」，优先采用，避免扫描页眉当题名
    file_title = title_from_filename(pdf.name)
    if any("\u4e00" <= c <= "\u9fff" for c in file_title) and 4 <= len(file_title) <= 80:
        title = file_title
    else:
        title = parsed.title if parsed.title != "未识别题名" else file_title
    authors = parsed.authors
    if "_" in pdf.stem:
        authors = [pdf.stem.rsplit("_", 1)[-1]]
    elif not authors:
        authors = parsed.authors

    meta = {
        "paper_id": paper_id,
        "sha256": digest,
        "source_path": rel,
        "file_name": pdf.name,
        "source_type": config.get("corpus", {}).get("source_type", "preset"),
        "is_preset": True,
        "is_public": True,
        "title": title,
        "authors": authors,
        "year": parsed.year,
        "abstract": parsed.abstract,
        "page_count": parsed.page_count,
        "section_recognized": parsed.section_recognized,
        "section_tree": [
            {
                "title": n.title,
                "page_start": n.page_start,
                "page_end": n.page_end,
            }
            for n in parsed.section_tree
        ],
        "chunk_count": len(chunks),
        "status": "indexed",
        "indexed_at": utc_now(),
        "storage_key": f"papers/{paper_id}/source.pdf",
        "domain": config.get("domain", {}).get("name"),
    }
    save_json(meta_path, meta)
    save_json(paper_dir / "chunks.json", chunks)
    # 全文单独存放，不进入清单摘要
    (paper_dir / "full_text.txt").write_text(parsed.full_text, encoding="utf-8")

    return {
        "path": rel,
        "paper_id": paper_id,
        "sha256": digest,
        "status": "indexed",
        "title": title,
        "authors": authors,
        "year": parsed.year,
        "page_count": parsed.page_count,
        "chunk_count": len(chunks),
        "section_recognized": parsed.section_recognized,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="增量同步预置论文到公用知识库")
    parser.add_argument("--papers-dir", default=None, help="PDF 目录，默认读配置或 论文/")
    parser.add_argument("--config", default=str(ROOT / "deploy" / "corpus.yaml"))
    parser.add_argument("--data-dir", default=str(ROOT / "data"))
    parser.add_argument("--dry-run", action="store_true", help="只扫描，不写入")
    parser.add_argument(
        "--reparse",
        nargs="*",
        default=None,
        help="强制重解析指定相对/绝对路径；不带参数则重解析全部",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    config = load_yaml(config_path)

    papers_dir = Path(args.papers_dir or config.get("corpus", {}).get("papers_dir", "论文"))
    if not papers_dir.is_absolute():
        papers_dir = ROOT / papers_dir
    if not papers_dir.exists():
        print(f"[错误] 论文目录不存在: {papers_dir}")
        return 2

    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = ROOT / data_dir
    state_dir = data_dir / "corpus_state"
    storage_dir = data_dir / "storage"
    state_dir.mkdir(parents=True, exist_ok=True)
    storage_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = state_dir / "manifest.json"
    failed_path = state_dir / "failed.jsonl"
    report_path = state_dir / "last_sync_report.json"
    manifest = load_json(manifest_path, {"papers": {}, "updated_at": None})

    pdfs = list_pdfs(papers_dir)
    force_all = args.reparse is not None and len(args.reparse) == 0
    force_set = set()
    if args.reparse:
        for item in args.reparse:
            p = Path(item)
            if not p.is_absolute():
                p = ROOT / p
            force_set.add(p.resolve())

    print(f"领域: {config.get('domain', {}).get('name')}")
    print(f"扫描: {papers_dir}  共 {len(pdfs)} 个 PDF")
    if args.dry_run:
        print("模式: dry-run（不写入）")

    summary = {"indexed": 0, "skipped": 0, "failed": 0, "items": []}

    for pdf in pdfs:
        force = force_all or pdf.resolve() in force_set
        digest = sha256_file(pdf)
        known = manifest.get("papers", {}).get(digest)
        if known and known.get("status") == "indexed" and not force and not args.dry_run:
            summary["skipped"] += 1
            summary["items"].append(
                {
                    "path": str(pdf.relative_to(ROOT)),
                    "status": "skipped",
                    "title": known.get("title"),
                    "sha256": digest,
                }
            )
            continue

        if args.dry_run:
            status = "would_reparse" if (known or force) else "would_index"
            print(f"[{status}] {pdf.relative_to(ROOT)}")
            summary["items"].append({"path": str(pdf.relative_to(ROOT)), "status": status, "sha256": digest})
            continue

        result = process_one(
            pdf,
            root=ROOT,
            storage_dir=storage_dir,
            papers_dir=papers_dir,
            config=config,
            force=force,
        )
        summary["items"].append(result)
        status = result["status"]
        if status == "indexed":
            summary["indexed"] += 1
            manifest["papers"][result["sha256"]] = {
                "paper_id": result["paper_id"],
                "path": result["path"],
                "title": result.get("title"),
                "authors": result.get("authors"),
                "year": result.get("year"),
                "status": "indexed",
                "indexed_at": utc_now(),
            }
            print(f"[indexed] {result.get('title')}  chunks={result.get('chunk_count')}")
        elif status == "skipped":
            summary["skipped"] += 1
            print(f"[skipped] {result.get('title') or result['path']}")
        else:
            summary["failed"] += 1
            append_jsonl(
                failed_path,
                {"at": utc_now(), **result},
            )
            print(f"[failed] {result['path']}  {result.get('error')}")

    if not args.dry_run:
        manifest["updated_at"] = utc_now()
        manifest["domain"] = config.get("domain", {})
        manifest["count"] = {
            "total_files": len(pdfs),
            "indexed": len([p for p in manifest["papers"].values() if p.get("status") == "indexed"]),
        }
        save_json(manifest_path, manifest)

    report = {
        "at": utc_now(),
        "papers_dir": str(papers_dir),
        "dry_run": args.dry_run,
        "summary": {
            "scanned": len(pdfs),
            "indexed": summary["indexed"],
            "skipped": summary["skipped"],
            "failed": summary["failed"],
        },
        "items": summary["items"],
    }
    save_json(report_path, report)
    print(
        f"完成: scanned={len(pdfs)} indexed={summary['indexed']} "
        f"skipped={summary['skipped']} failed={summary['failed']}"
    )
    print(f"清单: {manifest_path}")
    print(f"报告: {report_path}")
    return 1 if summary["failed"] and not args.dry_run else 0


if __name__ == "__main__":
    raise SystemExit(main())
