"""Tavily 联网搜索。"""
from __future__ import annotations

from tavily import TavilyClient


class TavilySearch:
    """封装 Tavily，返回格式化后的搜索上下文。"""

    def __init__(self, api_key: str, max_results: int = 5):
        self._client = TavilyClient(api_key=api_key)
        self._max_results = max_results

    def search(self, query: str) -> str:
        """搜索并返回拼接好的上下文文本。"""
        print(
            f"[WEB] Searching: {query}",
            flush=True,
        )

        result = self._client.search(
            query=query,
            search_depth="basic",
            max_results=self._max_results,
        )

        results = (
            result.get("results", [])
            if isinstance(result, dict)
            else getattr(result, "results", []) or []
        )

        context = []

        for index, item in enumerate(results, start=1):
            context.append(
                f"[{index}] {item.get('title', '')}\n"
                f"{item.get('content', '')}\n"
                f"来源: {item.get('url', '')}"
            )

        return "\n\n".join(context)
