"""Root installer CLI for agy-usage-monitor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agy_usage_monitor.installer import install, status_summary, uninstall
from agy_usage_monitor.state import set_dashboard_enabled


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install or manage agy-usage-monitor for Antigravity CLI.")
    parser.add_argument(
        "action",
        nargs="?",
        default="install",
        choices=["install", "uninstall", "status", "enable", "disable"],
        help="Action to perform (default: install)",
    )
    parser.add_argument("--config-dir", type=Path, default=None, help="Override ~/.gemini/antigravity-cli path")
    parser.add_argument("--no-skills", action="store_true", help="Do not install agy-usage / agy-dashboard skills")
    parser.add_argument("--keep-skills", action="store_true", help="Keep installed skills on uninstall")
    args = parser.parse_args(argv)

    if args.action == "install":
        result = install(config_dir=args.config_dir, with_skills=not args.no_skills)
        print("Installed agy-usage-monitor:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.action == "uninstall":
        result = uninstall(config_dir=args.config_dir, keep_skills=args.keep_skills)
        print("Uninstalled agy-usage-monitor:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
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

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
