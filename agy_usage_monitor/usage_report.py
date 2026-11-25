"""Detailed usage report generator for Antigravity CLI."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agy_usage_monitor.dashboard import format_duration, format_tokens
from agy_usage_monitor.state import (
    STATS_FILENAME,
    compute_daily_burn_rate,
    get_config_dir,
    is_dashboard_enabled,
    read_json,
)


def _count_history_prompts(config_dir: Path) -> int:
    history_path = config_dir / "history.jsonl"
    if not history_path.is_file():
        return 0
    try:
        with history_path.open("r", encoding="utf-8", errors="replace") as handle:
            return sum(1 for line in handle if line.strip())
    except OSError:
        return 0


def build_usage_report(config_dir: Path | None = None, days: int = 7) -> str:
    """Build a human-readable usage report from local Antigravity stats."""
    cfg = get_config_dir(config_dir)
    stats = read_json(cfg / STATS_FILENAME, default={})
    if not isinstance(stats, dict):
        stats = {}

    daily: dict[str, Any] = stats.get("daily", {}) if isinstance(stats.get("daily"), dict) else {}
    sessions: dict[str, Any] = stats.get("sessions", {}) if isinstance(stats.get("sessions"), dict) else {}

    enabled = is_dashboard_enabled(cfg)
    burn_rate = compute_daily_burn_rate(daily, days=days)
    history_prompts = _count_history_prompts(cfg)

    lines = [
        "Antigravity Usage Report",
        "=" * 40,
        f"Config dir     : {cfg}",
        f"Dashboard      : {'enabled' if enabled else 'disabled'}",
        f"Tracked sessions: {len(sessions)}",
        f"History entries : {history_prompts}",
        f"Avg burn ({days}d)  : {format_tokens(burn_rate)} tokens/day" if burn_rate > 0 else f"Avg burn ({days}d)  : --",
        "",
        f"Daily Breakdown (last {days} days)",
        "-" * 40,
    ]

    recent_days = sorted(daily.keys())[-days:]
    if not recent_days:
        lines.append("No daily usage recorded yet. Start an `agy` session with the statusLine enabled.")
    else:
        for day_key in recent_days:
            entry = daily.get(day_key, {})
            tok = int(entry.get("tokens", 0))
            cost = float(entry.get("cost_usd", 0.0))
            sess = int(entry.get("sessions", 0))
            lines.append(f"{day_key}  {format_tokens(tok):>8} tokens  ${cost:>7.3f}  ({sess} sessions)")

    if sessions:
        lines.extend(["", "Recent Sessions (top 5)", "-" * 40])
        ordered = sorted(
            sessions.items(),
            key=lambda item: float(item[1].get("last_seen", 0)) if isinstance(item[1], dict) else 0.0,
            reverse=True,
        )[:5]
        for conv_id, sdata in ordered:
            if not isinstance(sdata, dict):
                continue
            tok = int(sdata.get("input_tokens", 0)) + int(sdata.get("output_tokens", 0))
            cost = float(sdata.get("cost_usd", 0.0))
            model = sdata.get("model") or "unknown"
            project = sdata.get("project") or "-"
            dur = max(0, int(float(sdata.get("last_seen", 0)) - float(sdata.get("started_at", 0))))
            ts = datetime.fromtimestamp(float(sdata.get("last_seen", 0)), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            lines.append(
                f"{conv_id[:8]}  {ts}  {project:<16}  {model:<22}  {format_tokens(tok):>7}  ${cost:.3f}  ({format_duration(dur)})"
            )

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show Antigravity CLI usage report.")
    parser.add_argument("--days", type=int, default=7, help="Number of recent days to include (default: 7)")
    parser.add_argument("--json", action="store_true", help="Output raw stats JSON")
    args = parser.parse_args(argv)

    cfg = get_config_dir()
    if args.json:
        stats = read_json(cfg / STATS_FILENAME, default={})
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    else:
        print(build_usage_report(config_dir=cfg, days=max(1, args.days)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
