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
            print("[2/5] ✓ 命中同版本 AI 缓存，无需重新调用 DeepSeek")
            return cache_obj
        print(
            f"[2/5] 发现旧缓存 {cache_obj.get('schema_version', 'unknown')}，"
            f"当前 {SCHEMA_VERSION}，将重新分析"
        )

    print("[2/5] 解析 PDF ...")
    pages = parse_pdf(pdf)
    max_chars = int(os.getenv("MAX_ANALYSIS_CHARS", "120000"))
    text = select_analysis_text(pages, max_chars=max_chars)
    if len(text) < 1000:
        raise RuntimeError("PDF 可提取文本过少；可能是扫描版 PDF。V1 暂不自动 OCR。")

    print(f"      ✓ {len(pages)} 页，准备送入模型约 {len(text):,} 字符")
    print("[3/5] 调用 DeepSeek 进行结构化分析 ...")
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
    print("      ✓ DeepSeek 分析完成，结果已写入本地 cache")
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


def main():
    load_dotenv(ROOT / ".env", override=True)

    parser = argparse.ArgumentParser(description="PDF → DeepSeek → 飞书多维表格")
    parser.add_argument("pdf", help="论文 PDF 路径")
    parser.add_argument("--force-ai", action="store_true", help="忽略本地缓存，重新调用 DeepSeek")
    parser.add_argument("--update", action="store_true", help="如果飞书已存在相同 PaperHash，则覆盖更新")
    args = parser.parse_args()

    print(f"[0/5] Paper Ingest {SCHEMA_VERSION}")
    print(f"      时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    dry_run = validate_config()
    print(f"      模式：{'仅预览（DRY_RUN=1，不会写入飞书）' if dry_run else '真实写入飞书（DRY_RUN=0）'}")
    print(f"      模型：{os.getenv('DEEPSEEK_MODEL')}")
    print()

    pdf = Path(args.pdf).expanduser().resolve()
    if not pdf.exists() or pdf.suffix.lower() != ".pdf":
        raise RuntimeError(f"无效 PDF：{pdf}")

    print(f"[1/5] 读取论文：{pdf.name}")
    paper_hash = sha256_file(pdf)
    print(f"      SHA256：{paper_hash[:12]}…")

    cache_obj = load_or_analyze(pdf, paper_hash, args.force_ai)
    payload = feishu_payload(cache_obj, pdf)

    a = cache_obj["analysis"]
    print("[4/5] 解析结果预览")
    print("      标题：", a.get("title", ""))
    print("      简称：", a.get("short_name", ""))
    print("      Task：", "；".join(a.get("task", [])) or "-")
    print("      Domain：", "；".join(a.get("domain", [])) or "-")
    print("      Method：", "；".join(a.get("method", [])) or "-")
    print("      Type：", a.get("type", "") or "-")
    print("      Role：", a.get("role", "") or "-")
    if a.get("suggested_new_tags"):
        print("      建议新增标签：", "；".join(a["suggested_new_tags"]))

    if dry_run:
        print()
        print("[5/5] ⏸ 当前 DRY_RUN=1，因此没有写入飞书。")
        print("      如果你已经确认结果，打开 .env，把 DRY_RUN=0 后再拖一次 PDF。")
        return

    print()
    print("[5/5] 连接飞书并检查重复记录 ...")
    client = FeishuBitableClient()
    existing = client.find_by_hash(paper_hash)

    if existing:
        rid = existing["record_id"]
        if args.update:
            print(f"      发现已有记录 {rid}，正在覆盖更新 ...")
            client.update_record(rid, payload)
            print(f"      ✓ 飞书记录已更新：{rid}")
        else:
            print(f"      ✓ 飞书已存在相同 PDF：{rid}")
            print("      默认不重复写入。如需覆盖，请使用 --update。")
    else:
        print("      未发现重复记录，正在写入 ...")
        result = client.create_record(payload)
        record = result.get("data", {}).get("record", {})
        print("      ✓ 飞书写入完成：", record.get("record_id", "(record_id 未返回)"))


if __name__ == "__main__":
    log_path, log_file = start_logging()
    try:
        main()
        print(f"\n日志：{log_path}")
    except Exception as exc:
        print("\n================= ERROR =================")
        print(f"{type(exc).__name__}: {exc}")
        print("-----------------------------------------")
        traceback.print_exc()
        print("-----------------------------------------")
        print(f"完整日志已保存：{log_path}")
        print("把上面的 ERROR 区域或 logs/latest.log 发给我即可定位。")
        sys.exit(1)
    finally:
        log_file.flush()
