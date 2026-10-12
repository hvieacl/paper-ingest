from __future__ import annotations
import json
import os
import re
import time
from pathlib import Path

from openai import OpenAI
from pydantic import ValidationError

from deepseek_accounting import record_usage
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


class OutputLanguageError(ValueError):
    pass


def get_language_instruction() -> str:
    language = os.getenv("ANALYSIS_LANGUAGE", "zh-CN").strip() or "zh-CN"
    normalized = language.lower()

    if normalized in {"zh", "zh-cn", "zh_hans", "chinese", "简体中文"}:
        return (
            "默认使用简体中文。除专有名词和论文官方元数据外，"
            "所有解释、总结、判断、疑点和启发都必须使用简体中文。"
        )
    if normalized in {"en", "en-us", "english"}:
        return "Use English for all explanatory and analytical fields."
    return f"所有解释性字段统一使用 {language} 输出。"


def validate_output_language(analysis: PaperAnalysis) -> None:
    language = os.getenv("ANALYSIS_LANGUAGE", "zh-CN").strip() or "zh-CN"
    if language.lower() not in {"zh", "zh-cn", "zh_hans", "chinese", "简体中文"}:
        return

    fields = [
        analysis.research_problem,
        analysis.core_idea,
        analysis.pipeline,
        analysis.main_results,
        analysis.limitations,
        analysis.inspiration,
        *analysis.key_innovations,
        *analysis.questions,
    ]
    non_empty = [str(x).strip() for x in fields if str(x).strip()]
    if not non_empty:
        return

    chinese_fields = sum(bool(re.search(r"[\u4e00-\u9fff]", x)) for x in non_empty)
    # 允许公式、模型名和少量英文术语，但不能出现整份分析主体都是英文的情况。
    if chinese_fields < max(2, int(len(non_empty) * 0.6)):
        raise OutputLanguageError(
            "结构化分析主体未按 ANALYSIS_LANGUAGE=zh-CN 使用简体中文输出。"
        )


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
        language_instruction=get_language_instruction(),
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
                    "content": (
                        (
                            "上一次输出语言不符合要求。请严格按照系统提示中的输出语言重新生成；"
                            "不要把英文论文正文整段照搬到解释性字段中。\n\n"
                            if attempt > 0 and isinstance(last_error, OutputLanguageError)
                            else ""
                        )
                        + "请根据以下论文正文完成结构化分析，并仅输出 JSON：\n\n"
                        + text
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.0 if attempt > 0 else 0.2,
            max_tokens=max_tokens,
        )

        record_usage(resp.usage)
        choice = resp.choices[0]
        content = choice.message.content or ""
        finish_reason = getattr(choice, "finish_reason", None)

        if not content.strip():
            last_error = RuntimeError("DeepSeek 返回空内容。")
            continue

        try:
            data = json.loads(content)
            analysis = PaperAnalysis.model_validate(data)
            validate_output_language(analysis)
            return analysis
        except (json.JSONDecodeError, ValidationError, OutputLanguageError) as exc:
            last_error = exc

            if finish_reason == "length":
                print(
                    f"          ! DeepSeek 输出因长度被截断 "
                    f"(max_tokens={max_tokens})"
                )
            else:
                print(
                    f"          ! DeepSeek 结构化输出未通过校验："
                    f"{type(exc).__name__}: {exc}"
                )

    raise RuntimeError(
        f"DeepSeek 连续 {max_retries + 1} 次返回无法解析的结构化结果。"
        f"最后错误：{type(last_error).__name__}: {last_error}"
    )
