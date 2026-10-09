from __future__ import annotations
from pathlib import Path
import re
import pymupdf

SECTION_HINTS = [
    "abstract", "introduction", "method", "methodology", "approach",
    "framework", "architecture", "experiment", "evaluation", "ablation",
    "result", "discussion", "conclusion", "limitation", "future work",
]

REFERENCES_RE = re.compile(r"(?im)^\s*(references|bibliography)\s*$")

def parse_pdf(path: str | Path) -> list[str]:
    path = Path(path)
    doc = pymupdf.open(path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        # 去掉纯页码行和过多空白
        text = re.sub(r"(?m)^\s*\d+\s*$", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        pages.append(text)
    doc.close()
    return pages

def select_analysis_text(pages: list[str], max_chars: int = 120_000) -> str:
    """
    V1 的目标是高效结构化入库，不替代精读：
    - 保留前 4 页（通常覆盖摘要/引言）
    - 保留含 Method/Experiment/Ablation/Conclusion 等标题关键词的页面
    - 保留末尾 2 页正文（但尽量截掉 References）
    - 超长时按优先级截断
    """
    if not pages:
        return ""

    # 尽量从全文中截掉 References 之后内容
    full = "\n\n".join(f"[PAGE {i+1}]\n{p}" for i, p in enumerate(pages))
    m = REFERENCES_RE.search(full)
    if m:
        full_no_refs = full[:m.start()]
        # 如果截断后仍保留足够正文，则直接用于后续页面筛选的 fallback
        if len(full_no_refs) > 5000:
            full = full_no_refs

    selected_idx = set(range(min(4, len(pages))))
    for i, p in enumerate(pages):
        low = p.lower()
        if any(h in low for h in SECTION_HINTS):
            selected_idx.add(i)

    for i in range(max(0, len(pages) - 3), len(pages)):
        selected_idx.add(i)

    parts = []
    used = 0
    for i in sorted(selected_idx):
        p = pages[i]
        # 单页如果已经进入 references，跳过
        if i > 3 and re.search(r"(?im)^\s*(references|bibliography)\s*$", p):
            continue
        block = f"\n[PAGE {i+1}]\n{p}\n"
        if used + len(block) > max_chars:
            remain = max_chars - used
            if remain > 1500:
                parts.append(block[:remain])
            break
        parts.append(block)
        used += len(block)

    text = "".join(parts).strip()
    if len(text) < 5000:
        text = full[:max_chars]
    return text
