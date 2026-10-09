from __future__ import annotations
import json
import os
from openai import OpenAI
from schema import (
    PaperAnalysis, TASK_TAGS, DOMAIN_TAGS, REPRESENTATION_TAGS, METHOD_TAGS,
    RESOURCE_TYPES, PAPER_ROLES
)

SYSTEM_PROMPT = """\
你是一名计算机视觉、自动驾驶、三维重建与世界模型方向的科研论文分析助手。
你的任务不是写长篇读后感，而是把论文转换成可直接写入科研数据库的结构化 JSON。

研究主线：
场景表示与重建 → 动态场景与时空预测 → 生成式世界与场景生成 → 自动驾驶仿真与闭环 → 世界模型与多模态智能。

原则：
1. 严格依据论文正文；论文没有明确给出的信息填空字符串或空数组，不要编造。
2. 研究问题、核心思想、技术路线、关键创新必须互相区分，避免换句话重复。
3. 技术路线重点写清“输入 → 关键模块/处理 → 中间表示 → 输出 → 目的”，优先保留技术逻辑而不是背景叙述。
4. 关键创新只保留真正有区分度的 2-4 条。
5. main_results 只写实验真正支持的主要结论，不要泛化。
6. questions 是“读者精读时最值得继续解决的技术疑点”，2-5 条即可。
7. inspiration 要结合上述研究主线，指出这篇论文为什么值得我记住；不要写“具有参考价值”这类空话。
8. Task / Domain / Representation / Method 必须优先从给定词表选择；不要发明同义标签。
9. 如果确实缺少必要标签，只放到 suggested_new_tags，不要塞进正式标签。
10. 输出必须是合法 JSON，不要 Markdown，不要代码围栏。

允许的 Task：
{task_tags}

允许的 Domain：
{domain_tags}

允许的 Representation：
{representation_tags}

允许的 Method：
{method_tags}

允许的资源类型：
{resource_types}

允许的文献角色：
{paper_roles}

JSON 必须包含以下键：
{{
  "title": "",
  "short_name": "",
  "year": "",
  "authors": "",
  "venue": "",
  "arxiv_or_doi": "",
  "research_problem": "",
  "core_idea": "",
  "pipeline": "",
  "key_innovations": [],
  "main_results": "",
  "limitations": "",
  "questions": [],
  "inspiration": "",
  "task": [],
  "domain": [],
  "representation": [],
  "method": [],
  "resource_type": "研究论文",
  "paper_role": "方法论文",
  "suggested_new_tags": []
}}
""".format(
    task_tags="；".join(TASK_TAGS),
    domain_tags="；".join(DOMAIN_TAGS),
    representation_tags="；".join(REPRESENTATION_TAGS),
    method_tags="；".join(METHOD_TAGS),
    resource_types="；".join(RESOURCE_TYPES),
    paper_roles="；".join(PAPER_ROLES),
)

def analyze_paper(text: str) -> PaperAnalysis:
    api_key = os.environ["DEEPSEEK_API_KEY"]
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = os.environ["DEEPSEEK_MODEL"]

    client = OpenAI(api_key=api_key, base_url=base_url)

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "请根据以下论文正文完成结构化分析，并仅输出 JSON：\n\n" + text},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=7000,
    )
    content = resp.choices[0].message.content or ""
    if not content.strip():
        raise RuntimeError("DeepSeek 返回空内容。请重试，或调整模型/提示词。")

    data = json.loads(content)
    return PaperAnalysis.model_validate(data)
