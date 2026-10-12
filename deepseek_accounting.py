from __future__ import annotations

import os
from typing import Any

import requests

_USAGE = {
    "requests": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "cache_hit_tokens": 0,
    "cache_miss_tokens": 0,
}


def _get(obj: Any, name: str, default=0):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def record_usage(usage: Any) -> None:
    if usage is None:
        return

    prompt_tokens = int(_get(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(_get(usage, "completion_tokens", 0) or 0)
    total_tokens = int(
        _get(usage, "total_tokens", prompt_tokens + completion_tokens)
        or (prompt_tokens + completion_tokens)
    )

    hit = int(_get(usage, "prompt_cache_hit_tokens", 0) or 0)
    miss = int(_get(usage, "prompt_cache_miss_tokens", 0) or 0)

    if hit == 0:
        details = _get(usage, "prompt_tokens_details", None)
        hit = int(_get(details, "cached_tokens", 0) or 0)

    if miss == 0 and prompt_tokens >= hit:
        miss = prompt_tokens - hit

    _USAGE["requests"] += 1
    _USAGE["prompt_tokens"] += prompt_tokens
    _USAGE["completion_tokens"] += completion_tokens
    _USAGE["total_tokens"] += total_tokens
    _USAGE["cache_hit_tokens"] += hit
    _USAGE["cache_miss_tokens"] += miss


def get_usage_summary() -> dict[str, int]:
    return dict(_USAGE)


def get_balance() -> dict:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")

    if not api_key:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY，无法查询余额。")

    response = requests.get(
        f"{base_url}/user/balance",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    if "is_available" not in data:
        raise RuntimeError(f"DeepSeek 余额接口返回异常：{data}")

    return data


def print_accounting_report() -> None:
    usage = get_usage_summary()

    print()
    print("=" * 72)
    print("DeepSeek 用量")
    print("=" * 72)
    print(f"API 请求：{usage['requests']}")
    print(f"输入 Tokens：{usage['prompt_tokens']:,}")
    print(f"  ├─ Cache Hit：{usage['cache_hit_tokens']:,}")
    print(f"  └─ Cache Miss：{usage['cache_miss_tokens']:,}")
    print(f"输出 Tokens：{usage['completion_tokens']:,}")
    print(f"总 Tokens：{usage['total_tokens']:,}")

    if os.getenv("QUERY_DEEPSEEK_BALANCE", "1").strip() != "1":
        return

    try:
        balance = get_balance()
        print()
        print("DeepSeek 余额：")
        infos = balance.get("balance_infos", [])
        if not infos:
            print("  （接口未返回余额明细）")
        for item in infos:
            currency = item.get("currency", "")
            total = item.get("total_balance", "")
            granted = item.get("granted_balance", "")
            topped = item.get("topped_up_balance", "")
            print(f"  {currency}：{total}")
            print(f"    ├─ 赠送余额：{granted}")
            print(f"    └─ 充值余额：{topped}")
        if not balance.get("is_available", False):
            print("  ! 当前账户余额不足，API 不可用")
    except Exception as exc:
        print()
        print(f"[WARN] DeepSeek 余额查询失败：{exc}")
