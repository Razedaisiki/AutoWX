"""把 Router + Tavily + 主模型串起来的应答器。

不再 monkey-patch AIClient.chat；而是提供一个带 chat() 接口的
WebAwareChat，交给 wx4py 的 AIResponder 使用。
"""
from __future__ import annotations

from wx4py import AIResponder

from .prompts import WEB_CONTEXT_PROMPT
from .router import SearchDecision, decide_web_search, should_force_search
from .search import TavilySearch


class WebAwareChat:
    """暴露 wx4py AIResponder 需要的 chat(messages) 接口。

    流程：关键词强联网 → MiMo 判断 → Tavily → 主模型回答。
    """

    def __init__(self, answer_client, router_ai, search_provider: TavilySearch):
        self._answer = answer_client
        self._router = router_ai
        self._search = search_provider

    def chat(self, messages):
        user_text = ""

        for message in reversed(messages):
            if message.get("role") == "user":
                user_text = message.get("content", "")
                break

        if not user_text:
            return self._answer.chat(messages)

        # 第一优先级：关键词强制联网
        if should_force_search(user_text):
            decision = SearchDecision(
                should_search=True,
                query=user_text,
                reason="keyword",
            )
            print("[ROUTER] Force search by keyword", flush=True)
        else:
            decision = decide_web_search(self._router, user_text)
            print(
                f"[ROUTER] search={decision.should_search}, "
                f"query={decision.query}",
                flush=True,
            )

        if not decision.should_search:
            return self._answer.chat(messages)

        # 联网
        try:
            web_context = self._search.search(decision.query)

            if not web_context:
                print("[WEB] No results", flush=True)
                return self._answer.chat(messages)

            augmented_messages = [
                {
                    "role": "system",
                    "content": WEB_CONTEXT_PROMPT + web_context,
                }
            ] + list(messages)

            return self._answer.chat(augmented_messages)

        except Exception as exc:
            print(
                f"[WEB] Search failed: {exc!r}",
                flush=True,
            )
            return self._answer.chat(messages)


def build_responder(config, answer_client, router_ai, search_provider):
    """组装 wx4py 的 AIResponder。"""
    chat = WebAwareChat(answer_client, router_ai, search_provider)

    return AIResponder(
        chat,
        context_size=config.context_size,
        reply_on_at=True,
    )
