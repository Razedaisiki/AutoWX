"""微信运行时生命周期。"""
from __future__ import annotations

import time

from wx4py import AsyncCallbackHandler, WeChatClient

from ..config import Config
from .groups import build_group_nicknames
from .watchdog import wait_until_phone_logs_out
from .wx4py_compat import apply_wx4py_workarounds


def run_wechat(config: Config, responder) -> None:
    """连接微信、应用兼容补丁、启动群监听、等待退出。"""
    handler = AsyncCallbackHandler(responder, auto_reply=True)

    print(
        "Connecting to WeChat...",
        flush=True,
    )

    with WeChatClient(auto_connect=True) as wx:

        print(
            "wx4py is_connected:",
            wx.is_connected,
            flush=True,
        )

        if not wx.is_connected:
            raise RuntimeError("wx4py connection failed.")

        print()
        print("=" * 70, flush=True)
        print("VXBot ONLINE", flush=True)
        print("=" * 70, flush=True)

        for group in config.groups:
            print(f"Listening group: {group}", flush=True)

        print("Trigger: @机器人 + 问题", flush=True)
        print("Stop: 手机微信退出 Windows 微信", flush=True)
        print("=" * 70, flush=True)

        # 连接成功后等待微信界面稳定再开始监听
        print("Settling WeChat UI (5s)...", flush=True)
        time.sleep(5)

        apply_wx4py_workarounds(wx, config.groups)

        processor = wx.process_groups(
            config.groups,
            [handler],
            block=False,
            group_nicknames=build_group_nicknames(
                config.groups,
                config.bot_nickname,
            ),
        )

        wait_until_phone_logs_out(
            processor,
            check_interval=1.0,
            confirm_seconds=5,
        )

    print()
    print("=" * 70, flush=True)
    print("VXBot finished normally.", flush=True)
    print("=" * 70, flush=True)
