"""配置解析测试。"""
import pytest

from autowx.config import ConfigurationError, load_config

REQUIRED = {
    "MODEL_API_KEY": "sk-test",
    "MODEL_API_BASE": "https://api.example.com/v1",
    "MODEL_NAME": "deepseek-v4-flash",
    "TAVILY_API_KEY": "tvly-test",
    "VX_GROUPS_JSON": '["群1", "群2"]',
}


def _clear_env(monkeypatch):
    for key in list(REQUIRED) + ["ROUTER_MODEL", "BOT_NICKNAME", "BOT_CONTEXT_SIZE"]:
        monkeypatch.delenv(key, raising=False)


def _set_env(monkeypatch, **overrides):
    env = dict(REQUIRED)
    env.update(overrides)
    for key, value in env.items():
        monkeypatch.setenv(key, value)


def test_load_config_basic(monkeypatch):
    _clear_env(monkeypatch)
    _set_env(monkeypatch)

    config = load_config()

    assert config.model == "deepseek-v4-flash"
    assert config.router_model == "mimo-v2.5"
    assert config.bot_nickname == "bot"
    assert config.groups == ["群1", "群2"]
    assert config.context_size == 8


def test_load_config_custom(monkeypatch):
    _clear_env(monkeypatch)
    _set_env(
        monkeypatch,
        ROUTER_MODEL="mimo-v3",
        BOT_NICKNAME="小V",
        BOT_CONTEXT_SIZE="20",
    )

    config = load_config()

    assert config.router_model == "mimo-v3"
    assert config.bot_nickname == "小V"
    assert config.context_size == 20


def test_missing_required_key(monkeypatch):
    _clear_env(monkeypatch)
    _set_env(monkeypatch)

    monkeypatch.delenv("TAVILY_API_KEY")

    with pytest.raises(ConfigurationError):
        load_config()


def test_invalid_groups_json(monkeypatch):
    _clear_env(monkeypatch)
    _set_env(monkeypatch, VX_GROUPS_JSON="not-json")

    with pytest.raises(ConfigurationError):
        load_config()


def test_groups_not_array(monkeypatch):
    _clear_env(monkeypatch)
    _set_env(monkeypatch, VX_GROUPS_JSON='{"a": 1}')

    with pytest.raises(ConfigurationError):
        load_config()
