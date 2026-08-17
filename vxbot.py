"""AutoWX 入口。

兼容直接运行 `python vxbot.py`：把 src/ 加入 sys.path 后调用包入口。
推荐使用 `python -m autowx`（需先 `pip install -e .`）。
"""
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from autowx.app import run  # noqa: E402


if __name__ == "__main__":
    try:
        run()

    except KeyboardInterrupt:
        print("VXBot interrupted.", flush=True)

    except Exception:
        print("VXBot fatal error:", flush=True)
        traceback.print_exc()
        sys.exit(1)
