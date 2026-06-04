"""Verify Phase 0 system dependencies.

Imports each required runtime dependency, reports its version, and on
Linux also reports whether a /dev/video* device is available so the
webcam is wired up.

Exit code:
    0 — all required imports succeeded
    1 — at least one required package is missing
"""

import importlib
import platform
import sys
from pathlib import Path

REQUIRED = [
    "cv2",
    "mediapipe",
    "bleak",
    "fastapi",
    "uvicorn",
    "pydantic",
    "requests",
]


def main() -> int:
    print(f"python {sys.version.split()[0]} on {platform.platform()}")
    print()

    missing: list[str] = []
    for name in REQUIRED:
        try:
            mod = importlib.import_module(name)
            version = getattr(mod, "__version__", "?")
            print(f"  ok    {name:12s} {version}")
        except ImportError as exc:
            print(f"  FAIL  {name:12s} {exc}")
            missing.append(name)

    if platform.system() == "Linux":
        videos = sorted(Path("/dev").glob("video*"))
        if videos:
            print(f"  ok    webcam       {', '.join(str(v) for v in videos)}")
        else:
            print("  WARN  webcam       no /dev/video* device found")

    print()
    if missing:
        print(f"missing: {', '.join(missing)}")
        print("run: pip install -r requirements.txt")
        return 1
    print("environment ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
