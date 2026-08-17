"""python -m autowx 入口。"""
import sys
import traceback

from .app import run


if __name__ == "__main__":
    try:
        run()

    except KeyboardInterrupt:
        print("VXBot interrupted.", flush=True)

    except Exception:
        print("VXBot fatal error:", flush=True)
        traceback.print_exc()
        sys.exit(1)
