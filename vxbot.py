import os
import sys
import json
import time
import ctypes
import traceback

import win32gui


# ============================================================
# UTF-8
# ============================================================

try:
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="backslashreplace",
    )
except Exception:
    pass

try:
    sys.stderr.reconfigure(
        encoding="utf-8",
        errors="backslashreplace",
    )
except Exception:
    pass


from wx4py import (
    AIClient,
    AIConfig,
    AIResponder,
    AsyncCallbackHandler,
    WeChatClient,
)

from wx4py.core.win32 import (
    find_wechat_window,
    get_window_class,
)


# ============================================================
# Config
# ============================================================

def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value


def load_groups():
    raw = require_env("VX_GROUPS_JSON")

    try:
        groups = json.loads(raw)
    except Exception as exc:
        raise RuntimeError(
            'VX_GROUPS_JSON must look like ["群1","群2"]'
        ) from exc

    if not isinstance(groups, list):
        raise RuntimeError(
            "VX_GROUPS_JSON must be a JSON array."
        )

    groups = [
        str(item).strip()
        for item in groups
        if str(item).strip()
    ]

    if not groups:
        raise RuntimeError(
            "No groups configured."
        )

    return groups


# ============================================================
# WeChat login-state watchdog
# ============================================================

def inspect_wechat_window():
    """
    返回：
        ("online", hwnd, class_name)
        ("login", hwnd, class_name)
        ("missing", None, None)
        ("unknown", hwnd, class_name)

    wx4py 自己也是依赖窗口类型来区分
    微信主界面与登录界面。
    """

    try:
        hwnd = find_wechat_window()
    except Exception as exc:
        print(
            f"[WATCHDOG] find_wechat_window error: {exc!r}",
            flush=True,
        )
        return "unknown", None, None

    if not hwnd:
        return "missing", None, None

    try:
        if not win32gui.IsWindow(hwnd):
            return "missing", None, None
    except Exception:
        return "missing", None, None

    try:
        cls = get_window_class(hwnd) or ""
    except Exception as exc:
        print(
            f"[WATCHDOG] GetClassName error: {exc!r}",
            flush=True,
        )
        return "unknown", hwnd, None

    # 已登录主界面
    if "MainWindow" in cls:
        return "online", hwnd, cls

    # 微信登录/未进入主界面的窗口
    if (
        "Login" in cls
        or "Qt" in cls
    ):
        return "login", hwnd, cls

    return "unknown", hwnd, cls


def wait_until_phone_logs_out(
    processor,
    check_interval=1.0,
    confirm_seconds=5,
):
    """
    手机端退出 Windows 微信后结束机器人。

    为避免微信切换窗口时偶发误判，
    要求连续 confirm_seconds 秒都处于非主窗口状态。
    """

    bad_since = None
    last_state = None
    last_cls = None

    print()
    print("=" * 70, flush=True)
    print("Logout watchdog started", flush=True)
    print(
        "手机端退出 Windows 微信后，CI 将自动结束。",
        flush=True,
    )
    print("=" * 70, flush=True)

    while True:

        state, hwnd, cls = inspect_wechat_window()

        # 状态发生变化才打印，避免 Actions 日志刷屏
        if state != last_state or cls != last_cls:

            hwnd_text = (
                hex(hwnd)
                if hwnd
                else "None"
            )

            print(
                f"[WATCHDOG] "
                f"state={state} "
                f"hwnd={hwnd_text} "
                f"class={cls!r}",
                flush=True,
            )

            last_state = state
            last_cls = cls

        # ------------------------------------------
        # 正常主界面
        # ------------------------------------------

        if state == "online":
            bad_since = None

        # ------------------------------------------
        # 登录界面 / 窗口消失
        # ------------------------------------------

        elif state in (
            "login",
            "missing",
        ):

            if bad_since is None:
                bad_since = time.monotonic()

                print(
                    "[WATCHDOG] "
                    "微信主界面已消失，开始确认退出状态...",
                    flush=True,
                )

            elapsed = (
                time.monotonic()
                - bad_since
            )

            if elapsed >= confirm_seconds:

                print()
                print("=" * 70, flush=True)
                print(
                    "Windows WeChat logged out.",
                    flush=True,
                )
                print(
                    "Stopping VXBot...",
                    flush=True,
                )
                print("=" * 70, flush=True)

                try:
                    processor.stop()

                    print(
                        "Group processor stopped.",
                        flush=True,
                    )

                except Exception as exc:

                    print(
                        f"processor.stop() warning: {exc!r}",
                        flush=True,
                    )

                return

        # ------------------------------------------
        # 不确定状态
        #
        # 不自动结束，避免一次 UIA/Win32 波动
        # 就误杀整个 CI。
        # ------------------------------------------

        else:
            bad_since = None

        time.sleep(check_interval)


# ============================================================
# VXBot
# ============================================================

def close_wechat_popup():
    """关闭 wx4py 重启微信后可能再次出现的弹窗"""
    try:
        hwnd = find_wechat_window()
        if not hwnd:
            return

        win32gui.SetForegroundWindow(hwnd)

        # 给微信弹窗一点时间稳定下来
        time.sleep(2)

        user32 = ctypes.windll.user32

        # ESC（按下 + 松开）
        user32.keybd_event(0x1B, 0, 0, 0)
        user32.keybd_event(0x1B, 0, 2, 0)

        time.sleep(2)
    except Exception as exc:
        print(
            f"[POPUP] close_wechat_popup warning: {exc!r}",
            flush=True,
        )


def main():

    print("=" * 70, flush=True)
    print("VXBot starting", flush=True)
    print("=" * 70, flush=True)

    api_key = require_env(
        "MODEL_API_KEY"
    )

    base_url = require_env(
        "MODEL_API_BASE"
    )

    model = require_env(
        "MODEL_NAME"
    )

    groups = load_groups()

    context_size = int(
        os.environ.get(
            "BOT_CONTEXT_SIZE",
            "8",
        )
    )

    print(
        "Model:",
        model,
        flush=True,
    )

    print(
        "API base:",
        base_url,
        flush=True,
    )

    print(
        "Groups:",
        groups,
        flush=True,
    )

    # ========================================================
    # AI
    # ========================================================

    ai = AIClient(
        AIConfig(
            base_url=base_url,
            api_format="completions",
            model=model,
            api_key=api_key,
            enable_thinking=False,
        )
    )

    responder = AIResponder(
        ai,
        context_size=context_size,

        # 只有 @ bot 时回复
        reply_on_at=True,
    )

    handler = AsyncCallbackHandler(
        responder,

        # 自动把模型答案发回群
        auto_reply=True,
    )

    # ========================================================
    # WeChat
    # ========================================================

    print(
        "Connecting to WeChat...",
        flush=True,
    )

    with WeChatClient(
        auto_connect=True
    ) as wx:

        print(
            "wx4py is_connected:",
            wx.is_connected,
            flush=True,
        )

        if not wx.is_connected:
            raise RuntimeError(
                "wx4py connection failed."
            )

        # wx4py 可能因为 RunningState 自动重启微信，
        # 重启后微信可能再次弹出更新/提示窗口。
        print(
            "Waiting for WeChat restart popup...",
            flush=True,
        )

        time.sleep(3)

        close_wechat_popup()

        print()
        print("=" * 70, flush=True)
        print("VXBot ONLINE", flush=True)
        print("=" * 70, flush=True)

        for group in groups:
            print(
                f"Listening group: {group}",
                flush=True,
            )

        print(
            "Trigger: @机器人 + 问题",
            flush=True,
        )

        print(
            "Stop: 手机微信退出 Windows 微信",
            flush=True,
        )

        print("=" * 70, flush=True)

        # ====================================================
        # 非阻塞启动群监听
        # ====================================================

        processor = wx.process_groups(
            groups,
            [handler],
            block=False,
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


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:

        print(
            "VXBot interrupted.",
            flush=True,
        )

    except Exception:

        print(
            "VXBot fatal error:",
            flush=True,
        )

        traceback.print_exc()

        sys.exit(1)
