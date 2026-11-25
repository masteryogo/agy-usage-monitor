"""Skill entrypoint to toggle or inspect the agy-usage-monitor dashboard."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _bootstrap_path() -> None:
    cfg_dir = Path(os.environ.get("AGY_CONFIG_DIR", Path.home() / ".gemini" / "antigravity-cli"))
    if cfg_dir.is_dir() and str(cfg_dir) not in sys.path:
        sys.path.insert(0, str(cfg_dir))


_bootstrap_path()

from agy_usage_monitor.state import is_dashboard_enabled, set_dashboard_enabled  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Control agy-usage-monitor statusLine dashboard.")
    parser.add_argument("action", choices=["on", "off", "toggle", "status"], default="status", nargs="?")
    args = parser.parse_args(argv)

    if args.action == "status":
        print(json.dumps({"enabled": is_dashboard_enabled()}, indent=2))
        return 0
    if args.action == "on":
        print(json.dumps(set_dashboard_enabled(True), indent=2))
        return 0
    if args.action == "off":
        print(json.dumps(set_dashboard_enabled(False), indent=2))
        return 0
    if args.action == "toggle":
        current = is_dashboard_enabled()
        print(json.dumps(set_dashboard_enabled(not current), indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
