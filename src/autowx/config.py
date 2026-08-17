"""集中读取并校验所有环境变量。

这是唯一读取 os.environ 的地方。缺 key 在启动时一次性报错，
而不是跑到一半才炸。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    """配置缺失或非法。"""


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigurationError(
            f"Missing required environment variable: {name}"
        )
    return value


def _load_groups(raw: str) -> list[str]:
    try:
        groups = json.loads(raw)
    except Exception as exc:
        raise ConfigurationError(
            'VX_GROUPS_JSON must look like ["群1","群2"]'
        ) from exc

    if not isinstance(groups, list):
        raise ConfigurationError(
            "VX_GROUPS_JSON must be a JSON array."
        )

    groups = [
        str(item).strip()
        for item in groups
        if str(item).strip()
    ]

    if not groups:
        raise ConfigurationError("No groups configured.")

    return groups


@dataclass(frozen=True)
class Config:
    api_key: str
    base_url: str
    model: str
    router_model: str
    tavily_api_key: str
    groups: list[str]
    bot_nickname: str
    context_size: int
    max_tokens: int
    router_max_tokens: int


def load_config() -> Config:
    """读取环境变量并返回配置对象。"""
    return Config(
        api_key=_require("MODEL_API_KEY"),
        base_url=_require("MODEL_API_BASE"),
        model=_require("MODEL_NAME"),
        router_model=os.environ.get("ROUTER_MODEL", "mimo-v2.5").strip()
        or "mimo-v2.5",
        tavily_api_key=_require("TAVILY_API_KEY"),
        groups=_load_groups(os.environ.get("VX_GROUPS_JSON", "")),
        bot_nickname=os.environ.get("BOT_NICKNAME", "bot").strip() or "bot",
        context_size=int(os.environ.get("BOT_CONTEXT_SIZE", "8")),
        max_tokens=int(os.environ.get("BOT_MAX_TOKENS", "32768")),
        router_max_tokens=int(os.environ.get("ROUTER_MAX_TOKENS", "1000")),
    )
