"""Unified CLI entrypoint for PyPI/uv installations of agy-usage-monitor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agy_usage_monitor.installer import install, status_summary, uninstall
from agy_usage_monitor.state import get_config_dir, set_dashboard_enabled
from agy_usage_monitor.usage_report import build_usage_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agy-usage-monitor",
        description="Real-time usage dashboard and report tool for Antigravity CLI (agy).",
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="install",
        choices=["install", "uninstall", "status", "enable", "disable", "report"],
        help="Action to perform (default: install)",
    )
    parser.add_argument("--config-dir", type=Path, default=None, help="Override ~/.gemini/antigravity-cli path")
    parser.add_argument("--no-skills", action="store_true", help="Do not install agy-usage / agy-dashboard skills")
    parser.add_argument("--keep-skills", action="store_true", help="Keep installed skills on uninstall")
    parser.add_argument("--days", type=int, default=7, help="Days to include in `report` (default: 7)")
    args = parser.parse_args(argv)

    if args.action == "install":
        print(json.dumps(install(config_dir=args.config_dir, with_skills=not args.no_skills), indent=2, ensure_ascii=False))
        return 0
    if args.action == "uninstall":
        print(json.dumps(uninstall(config_dir=args.config_dir, keep_skills=args.keep_skills), indent=2, ensure_ascii=False))
        return 0
    if args.action == "status":
        print(json.dumps(status_summary(config_dir=args.config_dir), indent=2, ensure_ascii=False))
        return 0
    if args.action == "enable":
        print(json.dumps(set_dashboard_enabled(True, config_dir=args.config_dir), indent=2))
        return 0
    if args.action == "disable":
        print(json.dumps(set_dashboard_enabled(False, config_dir=args.config_dir), indent=2))
        return 0
    if args.action == "report":
        cfg = get_config_dir(args.config_dir)
        print(build_usage_report(config_dir=cfg, days=max(1, args.days)))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
