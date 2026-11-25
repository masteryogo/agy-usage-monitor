"""Skill entrypoint for agy-usage."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _bootstrap_path() -> None:
    cfg_dir = Path(os.environ.get("AGY_CONFIG_DIR", Path.home() / ".gemini" / "antigravity-cli"))
    if cfg_dir.is_dir() and str(cfg_dir) not in sys.path:
        sys.path.insert(0, str(cfg_dir))


_bootstrap_path()

from agy_usage_monitor.usage_report import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
