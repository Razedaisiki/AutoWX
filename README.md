# AutoWX

微信群聊机器人，跑在 GitHub Actions 的 Windows runner 上，支持多群监听、`@机器人` 触发、联网搜索、Telegram 远程控制。

## 架构

```
Telegram /startvx
      │
      ▼
Cloudflare Worker (worker/telegram/)
      │ 调用 GitHub dispatch
      ▼
GitHub Actions (vxbot.yml)
      │  安装微信 → 扫码 → 截图二维码 → 发 Telegram
      ▼
wx4py 连接微信
      │
      ▼
autowx (Python 包)
      │  群监听 → @触发 → Router(MiMo) → Tavily → DeepSeek 回答
      ▼
另一个 workflow (vxbot-notify.yml) 结束时发 Telegram 通知
```

## 目录结构

```
src/autowx/
├── app.py             # 组装入口
├── config.py          # 唯一读取环境变量的地方
├── ai/                # 主模型、Router、Tavily、应答
└── wechat/            # 微信运行时、watchdog、wx4py 兼容层

scripts/windows/       # workflow 用的 PowerShell 脚本
worker/telegram/       # Cloudflare Worker
.github/workflows/     # vxbot.yml（主）+ vxbot-notify.yml（结束通知）
tests/                 # 不依赖微信 UI 的单元测试
```

## 环境变量

见 [.env.example](.env.example)。在 GitHub Actions 里通过 Secrets / Variables 配置：

- **Secrets**：`MODEL_API_KEY`、`TAVILY_API_KEY`、`TOKEN_GITHUB`（Fine-grained PAT，Actions: write）、`TELEGRAM_BOT_TOKEN`
- **Variables**：`MODEL_API_BASE`、`MODEL_NAME`、`VX_GROUPS_JSON`、`TELEGRAM_CHAT_ID`、`BOT_CONTEXT_SIZE`

## 运行

在 GitHub Actions 手动触发 `VXBot` workflow，或通过 Telegram 发 `/startvx`。

本地运行（需要 Windows + 已登录微信）：

```bash
pip install -e ".[test]"
python -m autowx
# 或
python vxbot.py
```

## 测试

```bash
pip install -e ".[test]"
pytest
```

## wx4py 兼容层

`src/autowx/wechat/wx4py_compat.py` 集中了针对 `wx4py==0.2.1` 的临时 workaround
（`open_chat` 对已打开群聊错误返回 `False`）。上游修复后可直接删除该文件。
