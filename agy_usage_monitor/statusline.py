"""Statusline entrypoint invoked by Antigravity CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from agy_usage_monitor.dashboard import render_dashboard
from agy_usage_monitor.models import StatusPayload
from agy_usage_monitor.state import is_dashboard_enabled, record_session_snapshot


def _ensure_utf8_stdio() -> None:
    for stream in (sys.stdin, sys.stdout):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def process_stdin(raw_text: str, config_dir: Path | None = None) -> str:
    """Parse a raw statusLine JSON string and return rendered output."""
    if not is_dashboard_enabled(config_dir=config_dir):
        return ""

    raw_text = raw_text.strip()
    if not raw_text:
        return ""

    try:
        data = json.loads(raw_text)
    except ValueError:
        return ""

    payload = StatusPayload.from_dict(data)
    duration_sec, burn_rate = record_session_snapshot(payload, config_dir=config_dir)
    return render_dashboard(payload, duration_sec=duration_sec, burn_rate_daily=burn_rate)


def main() -> int:
    """Read statusLine JSON from stdin and print the rendered dashboard."""
    _ensure_utf8_stdio()
    raw_text = sys.stdin.read()
    output = process_stdin(raw_text)
    if output:
        sys.stdout.write(output + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
