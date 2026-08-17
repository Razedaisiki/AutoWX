"""联网搜索路由：关键词强制 + MiMo 判断。"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

FORCE_SEARCH_KEYWORDS = [
    "搜一下",
    "搜索",
    "查一下",
    "查询",
    "联网",
    "上网查",
    "帮我查",
    "最新",
    "今天",
    "实时",
]


@dataclass
class SearchDecision:
    should_search: bool
    query: str
    reason: str = ""


def should_force_search(text: str) -> bool:
    """命中特殊关键词时直接联网，不问 Router。"""
    text = (text or "").lower()

    return any(
        keyword.lower() in text
        for keyword in FORCE_SEARCH_KEYWORDS
    )


def decide_web_search(router_ai, text: str) -> SearchDecision:
    """让 MiMo 判断是否需要联网。"""
    try:
        result = router_ai.chat([
            {"role": "user", "content": text},
        ])

        result = (result or "").strip()

        # 防止模型偶尔返回 ```json 包裹
        result = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            result,
            flags=re.IGNORECASE,
        )

        data = json.loads(result)

        return SearchDecision(
            should_search=bool(data.get("search")),
            query=str(data.get("query") or text),
            reason="router",
        )

    except Exception as exc:
        print(
            f"[ROUTER] failed: {exc!r}",
            flush=True,
        )

        # Router 出错时不影响正常聊天
        return SearchDecision(
            should_search=False,
            query=text,
            reason="router-fallback",
        )
