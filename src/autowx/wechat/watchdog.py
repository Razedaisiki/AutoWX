"""微信登录状态 watchdog：检测手机端退出并优雅结束。"""
from __future__ import annotations

import time

import win32gui
from wx4py.core.win32 import find_wechat_window


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
