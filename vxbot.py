import os
import sys
import json
import time
import threading
import traceback

from pathlib import Path

import win32gui
from PIL import ImageGrab


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
        ("online", hwnd, desc)   主界面（大窗口）
        ("login", hwnd, desc)    登录界面（小窗口）
        ("missing", None, None)  窗口不存在
        ("unknown", hwnd, desc)  无法判断

    通过窗口尺寸区分登录二维码窗口（约 296x388）和
    主界面（约 576x448）。两者 Win32 类名都是
    Qt51514QWindowIcon，无法靠类名区分。
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
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
    except Exception as exc:
        print(
            f"[WATCHDOG] GetWindowRect error: {exc!r}",
            flush=True,
        )
        return "unknown", hwnd, None

    desc = f"{width}x{height}"

    # 主界面明显更大（登录二维码窗口约 296x388）
    if width >= 500 and height >= 400:
        return "online", hwnd, desc

    return "login", hwnd, desc


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

def capture_debug_screens(stop_event):
    """每秒截一次屏，用于诊断 wx4py 重启微信期间发生了什么"""
    folder = Path("wx-debug-screens")
    folder.mkdir(exist_ok=True)

    index = 0

    while not stop_event.is_set() and index < 60:
        try:
            index += 1
            img = ImageGrab.grab(all_screens=True)
            name = f"{index:03d}_{time.strftime('%H-%M-%S')}.png"
            img.save(folder / name)

            print(
                f"[SCREENSHOT] {name}",
                flush=True,
            )
        except Exception as exc:
            print(
                f"[SCREENSHOT] failed: {exc!r}",
                flush=True,
            )

        stop_event.wait(1)


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

    screenshot_stop = threading.Event()

    screenshot_thread = threading.Thread(
        target=capture_debug_screens,
        args=(screenshot_stop,),
        daemon=True,
    )

    screenshot_thread.start()

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

        # 连接成功后等待微信界面稳定再开始监听
        print(
            "Settling WeChat UI (5s)...",
            flush=True,
        )

        time.sleep(5)

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
