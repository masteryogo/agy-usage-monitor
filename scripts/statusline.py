"""Thin statusline entrypoint copied to ~/.gemini/antigravity-cli/statusline.py."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure agy_usage_monitor is importable both when installed and from repo root
_HERE = Path(__file__).resolve().parent
for _candidate in (_HERE, _HERE.parent):
    if (_candidate / "agy_usage_monitor").is_dir() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

from agy_usage_monitor.statusline import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
