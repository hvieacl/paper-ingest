from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from pdf_parser import parse_pdf, select_analysis_text
from analyzer import analyze_paper
from feishu import FeishuBitableClient
from schema import FEISHU_FIELD_MAP, SCHEMA_VERSION

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache"
CACHE_DIR.mkdir(exist_ok=True)


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
            print("✓ 命中本地 AI 缓存")
            return cache_obj
        print(
            f"• 发现旧缓存版本 {cache_obj.get('schema_version', 'unknown')}，"
            f"当前版本为 {SCHEMA_VERSION}，将重新分析"
        )

    print("• 解析 PDF ...")
    pages = parse_pdf(pdf)
    max_chars = int(os.getenv("MAX_ANALYSIS_CHARS", "120000"))
    text = select_analysis_text(pages, max_chars=max_chars)
    if len(text) < 1000:
        raise RuntimeError("PDF 可提取文本过少；可能是扫描版 PDF。V1 暂不自动 OCR。")

    print(f"✓ PDF 文本准备完成：{len(pages)} 页，送模约 {len(text):,} 字符")
    print("• DeepSeek 结构化分析 ...")
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
    print("✓ DeepSeek 分析完成并缓存")
    return cache_obj


def feishu_payload(cache_obj: dict, pdf: Path) -> dict:
    a = cache_obj["analysis"]
    payload = {}

    for feishu_name, json_name in FEISHU_FIELD_MAP.items():
        v = a.get(json_name)
        if isinstance(v, list):
            # 四维分类中 Task / Domain / Method 为多选；其余列表写成长文本。
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
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="PDF → DeepSeek → 飞书多维表格")
    parser.add_argument("pdf", help="论文 PDF 路径")
    parser.add_argument(
        "--force-ai",
        action="store_true",
        help="忽略本地缓存，重新调用 DeepSeek",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="如果飞书已存在相同 PaperHash，则覆盖更新",
    )
    args = parser.parse_args()

    pdf = Path(args.pdf).expanduser().resolve()
    if not pdf.exists() or pdf.suffix.lower() != ".pdf":
        raise SystemExit(f"无效 PDF：{pdf}")

    paper_hash = sha256_file(pdf)
    print(f"\n论文：{pdf.name}")
    print(f"Hash：{paper_hash[:12]}…")

    cache_obj = load_or_analyze(pdf, paper_hash, args.force_ai)
    payload = feishu_payload(cache_obj, pdf)

    a = cache_obj["analysis"]
    print("\n--- 解析预览 ---")
    print("标题：", a.get("title", ""))
    print("简称：", a.get("short_name", ""))
    print("Task：", "；".join(a.get("task", [])))
    print("Domain：", "；".join(a.get("domain", [])))
    print("Method：", "；".join(a.get("method", [])))
    print("Type：", a.get("type", ""))
    print("Role：", a.get("role", ""))
    if a.get("suggested_new_tags"):
        print("建议新增标签：", "；".join(a["suggested_new_tags"]))

    if os.getenv("DRY_RUN", "1") == "1":
        print("\nDRY_RUN=1：未写入飞书。写入预览已保存到 cache。")
        print("确认飞书字段和解析结果无误后，把 .env 中 DRY_RUN 改为 0。")
        return

    client = FeishuBitableClient()
    existing = client.find_by_hash(paper_hash)

    if existing:
        rid = existing["record_id"]
        if args.update:
            print(f"\n• 飞书中已存在，更新 {rid} ...")
            client.update_record(rid, payload)
            print("✓ 飞书记录已更新")
        else:
            print(f"\n✓ 飞书已存在相同 PDF（record_id={rid}），跳过写入。")
            print("  如需覆盖：加 --update")
    else:
        print("\n• 写入飞书 ...")
        result = client.create_record(payload)
        record = result.get("data", {}).get("record", {})
        print("✓ 飞书写入完成：", record.get("record_id", "(record_id 未返回)"))


if __name__ == "__main__":
    main()
