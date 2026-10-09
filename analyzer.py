from __future__ import annotations
import json
import os
import time
from pathlib import Path

from openai import OpenAI
from pydantic import ValidationError

from schema import (
    PaperAnalysis,
    TASK_TAGS,
    DOMAIN_TAGS,
    METHOD_TAGS,
    TYPE_TAGS,
    ROLE_TAGS,
)

ROOT = Path(__file__).resolve().parent
PROMPT_PATH = ROOT / "prompts" / "paper_analysis_system.txt"


def load_system_prompt() -> str:
    if not PROMPT_PATH.exists():
        raise RuntimeError(f"找不到提示词文件：{PROMPT_PATH}")

    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.format(
        task_tags="；".join(TASK_TAGS),
        domain_tags="；".join(DOMAIN_TAGS),
        method_tags="；".join(METHOD_TAGS),
        type_tags="；".join(TYPE_TAGS),
        role_tags="；".join(ROLE_TAGS),
    )


def analyze_paper(text: str) -> PaperAnalysis:
    api_key = os.environ["DEEPSEEK_API_KEY"]
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = os.environ["DEEPSEEK_MODEL"]
    max_tokens = int(os.getenv("DEEPSEEK_MAX_TOKENS", "7000"))
    max_retries = int(os.getenv("DEEPSEEK_MAX_RETRIES", "2"))

    client = OpenAI(api_key=api_key, base_url=base_url)
    system_prompt = load_system_prompt()

    last_error = None

    for attempt in range(max_retries + 1):
        if attempt > 0:
            print(
                f"          ↻ DeepSeek 输出解析失败，正在重试 "
                f"({attempt}/{max_retries}) ..."
            )
            time.sleep(min(attempt, 2))

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": "请根据以下论文正文完成结构化分析，并仅输出 JSON：\n\n" + text,
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.0 if attempt > 0 else 0.2,
            max_tokens=max_tokens,
        )

        choice = resp.choices[0]
        content = choice.message.content or ""
        finish_reason = getattr(choice, "finish_reason", None)

        if not content.strip():
            last_error = RuntimeError("DeepSeek 返回空内容。")
            continue

        try:
            data = json.loads(content)
            return PaperAnalysis.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc

            if finish_reason == "length":
                print(
                    f"          ! DeepSeek 输出因长度被截断 "
                    f"(max_tokens={max_tokens})"
                )
            else:
                print(
                    f"          ! DeepSeek 返回的 JSON 不合法："
                    f"{type(exc).__name__}: {exc}"
                )

    raise RuntimeError(
        f"DeepSeek 连续 {max_retries + 1} 次返回无法解析的结构化结果。"
        f"最后错误：{type(last_error).__name__}: {last_error}"
    )
