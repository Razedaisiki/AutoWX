"""组装入口：读取配置、创建 AI 与微信运行时。"""
from __future__ import annotations

from .ai.clients import create_answer_client, create_router_client
from .ai.responder import build_responder
from .ai.search import TavilySearch
from .config import load_config
from .wechat.runtime import run_wechat


def run() -> None:
    config = load_config()

    print("=" * 70, flush=True)
    print("VXBot starting", flush=True)
    print("=" * 70, flush=True)

    print("Model:", config.model, flush=True)
    print("API base:", config.base_url, flush=True)
    print("Groups:", config.groups, flush=True)

    answer_client = create_answer_client(config)
    router_client = create_router_client(config)
    search_provider = TavilySearch(api_key=config.tavily_api_key)

    responder = build_responder(
        config,
        answer_client,
        router_client,
        search_provider,
    )

    run_wechat(config, responder)


if __name__ == "__main__":
    run()
