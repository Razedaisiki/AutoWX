"""创建 AI 客户端。"""
from __future__ import annotations

from wx4py import AIClient, AIConfig

from ..config import Config
from .prompts import ROUTER_PROMPT, SYSTEM_PROMPT


def create_answer_client(config: Config) -> AIClient:
    """主模型：DeepSeek，带思考。"""
    return AIClient(
        AIConfig(
            base_url=config.base_url,
            api_format="completions",
            model=config.model,
            api_key=config.api_key,
            enable_thinking=True,
            max_tokens=config.max_tokens,
            system_prompt=SYSTEM_PROMPT,
        )
    )


def create_router_client(config: Config) -> AIClient:
    """搜索路由器：MiMo，不思考，只做分类。"""
    return AIClient(
        AIConfig(
            base_url=config.base_url,
            api_format="completions",
            model=config.router_model,
            api_key=config.api_key,
            enable_thinking=False,
            max_tokens=config.router_max_tokens,
            system_prompt=ROUTER_PROMPT,
        )
    )
