"""wx4py==0.2.1 + 当前微信版本的兼容层。

Workaround: 微信 UI 实际已经打开群聊，但 open_chat() 会错误返回 False，
导致监听流程中断。这里对目标群强制返回 True，让监听继续。

Remove after upstream fix.
"""
from __future__ import annotations

import time


def apply_wx4py_workarounds(wx, groups: list[str]) -> None:
    """对 wx4py 实例应用兼容补丁。"""
    real_open_chat = wx.chat_window.open_chat

    def patched_open_chat(target, *args, **kwargs):
        result = real_open_chat(target, *args, **kwargs)

        if target in groups and not result:
            print(
                "[WX4PY-COMPAT] open_chat false-positive; overriding result",
                flush=True,
            )

            time.sleep(3)

            return True

        return result

    wx.chat_window.open_chat = patched_open_chat
