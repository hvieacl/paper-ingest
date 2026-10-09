from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from pdf_parser import parse_pdf, select_analysis_text
from analyzer import analyze_paper
from feishu import FeishuBitableClient
from schema import FEISHU_FIELD_MAP, SCHEMA_VERSION

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache"
LOG_DIR = ROOT / "logs"
CACHE_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def start_logging():
    log_path = LOG_DIR / "latest.log"
    log_file = log_path.open("w", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, log_file)
    sys.stderr = Tee(sys.__stderr__, log_file)
    return log_path, log_file


def require_env(name: str):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少配置：{name}。请检查项目目录中的 .env。")
    return value


def validate_config():
    require_env("DEEPSEEK_API_KEY")
    require_env("DEEPSEEK_MODEL")

    dry_run = os.getenv("DRY_RUN", "1").strip() == "1"
    if not dry_run:
        require_env("FEISHU_APP_ID")
        require_env("FEISHU_APP_SECRET")
        require_env("FEISHU_APP_TOKEN")
        require_env("FEISHU_TABLE_ID")
    return dry_run


def collect_pdfs(inputs: list[str]) -> list[Path]:
    """
    支持：
    - 一个或多个 PDF 文件
    - 一个或多个文件夹（只扫描该文件夹第一层 *.pdf）
    保留输入顺序，并去重。
    """
    result = []
    seen = set()

    for raw in inputs:
        path = Path(raw).expanduser().resolve()

        if path.is_dir():
            candidates = sorted(
                (p for p in path.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"),
                key=lambda p: p.name.lower(),
            )
        elif path.is_file() and path.suffix.lower() == ".pdf":
            candidates = [path]
        else:
            print(f"[WARN] 跳过无效输入：{path}")
            continue

        for pdf in candidates:
            key = str(pdf).lower()
            if key not in seen:
                seen.add(key)
                result.append(pdf)

    if not result:
        raise RuntimeError("没有找到可处理的 PDF。")
    return result


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_or_analyze(pdf: Path, paper_hash: str, force_ai: bool):
    cache_path = CACHE_DIR / f"{paper_hash}.json"

    if cache_path.exists() and not force_ai:
        cache_obj = json.loads(cache_path.read_text(encoding="utf-8"))
        if cache_obj.get("schema_version") == SCHEMA_VERSION:
            print("    [2/5] ✓ 命中同版本 AI 缓存，无需重新调用 DeepSeek")
            return cache_obj
        print(
            f"    [2/5] 发现旧缓存 {cache_obj.get('schema_version', 'unknown')}，"
            f"当前 {SCHEMA_VERSION}，将重新分析"
        )

    print("    [2/5] 解析 PDF ...")
    pages = parse_pdf(pdf)
    max_chars = int(os.getenv("MAX_ANALYSIS_CHARS", "120000"))
    text = select_analysis_text(pages, max_chars=max_chars)
    if len(text) < 1000:
        raise RuntimeError("PDF 可提取文本过少；可能是扫描版 PDF。V1 暂不自动 OCR。")

    print(f"          ✓ {len(pages)} 页，准备送入模型约 {len(text):,} 字符")
    print("    [3/5] 调用 DeepSeek 进行结构化分析 ...")
    analysis = analyze_paper(text)
    data = analysis.model_dump()

    cache_obj = {
        "schema_version": SCHEMA_VERSION,
        "paper_hash": paper_hash,
        "source_file": pdf.name,
        "analysis": data,
    }
    cache_path.write_text(
        json.dumps(cache_obj, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("          ✓ DeepSeek 分析完成，结果已写入本地 cache")
    return cache_obj


def feishu_payload(cache_obj: dict, pdf: Path) -> dict:
    a = cache_obj["analysis"]
    payload = {}

    for feishu_name, json_name in FEISHU_FIELD_MAP.items():
        v = a.get(json_name)
        if isinstance(v, list):
            if feishu_name in {"Task", "Domain", "Method"}:
                payload[feishu_name] = v
            else:
                payload[feishu_name] = "\n".join(
                    f"{i+1}. {x}" for i, x in enumerate(v)
                )
        elif v not in (None, ""):
            payload[feishu_name] = v

    payload.update(
        {
            "PaperHash": cache_obj["paper_hash"],
            "AI解析状态": "已解析",
            "解析版本": cache_obj.get("schema_version", SCHEMA_VERSION),
            "原文件名": pdf.name,
        }
    )
    return payload


def process_one(
    pdf: Path,
    *,
    index: int,
    total: int,
    dry_run: bool,
    force_ai: bool,
    update: bool,
    client: FeishuBitableClient | None,
    existing_by_hash: dict[str, dict],
):
    print()
    print("=" * 72)
    print(f"[{index}/{total}] {pdf.name}")
    print("=" * 72)

    print(f"    [1/5] 读取论文：{pdf.name}")
    paper_hash = sha256_file(pdf)
    print(f"          SHA256：{paper_hash[:12]}…")

    cache_obj = load_or_analyze(pdf, paper_hash, force_ai)
    payload = feishu_payload(cache_obj, pdf)

    a = cache_obj["analysis"]
    print("    [4/5] 解析结果预览")
    print("          标题：", a.get("title", ""))
    print("          简称：", a.get("short_name", ""))
    print("          Task：", "；".join(a.get("task", [])) or "-")
    print("          Domain：", "；".join(a.get("domain", [])) or "-")
    print("          Method：", "；".join(a.get("method", [])) or "-")
    print("          Type：", a.get("type", "") or "-")
    print("          Role：", a.get("role", "") or "-")
    if a.get("suggested_new_tags"):
        print("          建议新增标签：", "；".join(a["suggested_new_tags"]))

    if dry_run:
        print("    [5/5] ⏸ DRY_RUN=1：仅预览，不写入飞书")
        return "preview", a.get("title") or pdf.name

    assert client is not None
    print("    [5/5] 写入飞书 ...")
    existing = existing_by_hash.get(paper_hash)

    if existing:
        rid = existing["record_id"]
        if update:
            client.update_record(rid, payload)
            print(f"          ✓ 已覆盖更新：{rid}")
            return "updated", a.get("title") or pdf.name
        print(f"          ↷ 已存在，跳过：{rid}")
        return "skipped", a.get("title") or pdf.name

    result = client.create_record(payload)
    record = result.get("data", {}).get("record", {})
    rid = record.get("record_id", "")
    if rid:
        existing_by_hash[paper_hash] = record
    print("          ✓ 写入完成：", rid or "(record_id 未返回)")
    return "created", a.get("title") or pdf.name


def main():
    load_dotenv(ROOT / ".env", override=True)

    parser = argparse.ArgumentParser(description="PDF → DeepSeek → 飞书多维表格（支持批处理）")
    parser.add_argument(
        "inputs",
        nargs="+",
        help="一个或多个 PDF / 文件夹。文件夹会按文件名顺序处理第一层 PDF。",
    )
    parser.add_argument("--force-ai", action="store_true", help="忽略本地缓存，重新调用 DeepSeek")
    parser.add_argument("--update", action="store_true", help="飞书已存在相同 PaperHash 时覆盖更新")
    args = parser.parse_args()

    print(f"[0/5] Paper Ingest {SCHEMA_VERSION}")
    print(f"      时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    dry_run = validate_config()
    print(f"      模式：{'仅预览（DRY_RUN=1，不会写入飞书）' if dry_run else '真实写入飞书（DRY_RUN=0）'}")
    print(f"      模型：{os.getenv('DEEPSEEK_MODEL')}")

    pdfs = collect_pdfs(args.inputs)
    print(f"      待处理：{len(pdfs)} 篇")
    print("      策略：顺序处理；单篇失败不会中断后续任务")

    client = None
    existing_by_hash = {}

    if not dry_run:
        print("      正在读取飞书已有记录索引 ...")
        client = FeishuBitableClient()
        records = client.list_records()
        existing_by_hash = {
            str(rec.get("fields", {}).get("PaperHash", "")).strip(): rec
            for rec in records
            if str(rec.get("fields", {}).get("PaperHash", "")).strip()
        }
        print(f"      ✓ 已索引 {len(existing_by_hash)} 条已有 PaperHash")

    results = []
    failed = []

    for i, pdf in enumerate(pdfs, start=1):
        try:
            status, title = process_one(
                pdf,
                index=i,
                total=len(pdfs),
                dry_run=dry_run,
                force_ai=args.force_ai,
                update=args.update,
                client=client,
                existing_by_hash=existing_by_hash,
            )
            results.append((status, title, pdf.name))
        except Exception as exc:
            failed.append((pdf.name, str(exc)))
            print()
            print(f"    [FAILED] {pdf.name}")
            print(f"             {type(exc).__name__}: {exc}")
            traceback.print_exc()
            print("             → 继续处理下一篇")

    counts = {}
    for status, _, _ in results:
        counts[status] = counts.get(status, 0) + 1

    print()
    print("=" * 72)
    print("批处理完成")
    print("=" * 72)
    print(f"总计：{len(pdfs)}")
    if dry_run:
        print(f"预览成功：{counts.get('preview', 0)}")
    else:
        print(f"新建：{counts.get('created', 0)}")
        print(f"更新：{counts.get('updated', 0)}")
        print(f"已存在跳过：{counts.get('skipped', 0)}")
    print(f"失败：{len(failed)}")

    if failed:
        print()
        print("失败列表：")
        for name, error in failed:
            print(f"  - {name}: {error}")
        raise RuntimeError(f"批处理中有 {len(failed)} 篇失败，请查看上方错误或 logs/latest.log。")


if __name__ == "__main__":
    log_path, log_file = start_logging()
    try:
        main()
        print(f"\n日志：{log_path}")
    except Exception as exc:
        print("\n================= ERROR =================")
        print(f"{type(exc).__name__}: {exc}")
        print("-----------------------------------------")
        print(f"完整日志已保存：{log_path}")
        print("单篇失败不会阻塞其他论文；请根据“失败列表”定位具体文件。")
        sys.exit(1)
    finally:
        log_file.flush()
