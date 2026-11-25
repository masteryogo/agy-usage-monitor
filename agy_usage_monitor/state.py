"""State persistence and usage statistics tracking for Antigravity CLI."""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agy_usage_monitor.models import StatusPayload

STATE_FILENAME = "agy-usage-monitor-state.json"
STATS_FILENAME = "agy-usage-stats.json"
BACKUP_FILENAME = "agy-usage-monitor-backup.json"
MAX_STORED_SESSIONS = 200
MAX_STORED_DAYS = 30


def get_config_dir(override: Path | None = None) -> Path:
    """Return the Antigravity CLI config directory."""
    if override is not None:
        return override
    env_dir = os.environ.get("AGY_CONFIG_DIR")
    if env_dir:
        return Path(env_dir).expanduser()
    return Path.home() / ".gemini" / "antigravity-cli"


def read_json(path: Path, default: Any = None) -> Any:
    """Safely read a JSON file, returning `default` on missing or invalid data."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {} if default is None else default


def write_json_atomic(path: Path, data: Any) -> None:
    """Atomically write JSON to `path`, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def is_dashboard_enabled(config_dir: Path | None = None) -> bool:
    """Return whether the statusline dashboard is currently enabled."""
    state_path = get_config_dir(config_dir) / STATE_FILENAME
    data = read_json(state_path, default={})
    if not isinstance(data, dict):
        return True
    return bool(data.get("enabled", True))


def set_dashboard_enabled(enabled: bool, config_dir: Path | None = None) -> dict[str, Any]:
    """Persist the dashboard enabled state and return the updated state dict."""
    state_path = get_config_dir(config_dir) / STATE_FILENAME
    data = read_json(state_path, default={})
    if not isinstance(data, dict):
        data = {}
    data["enabled"] = bool(enabled)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_json_atomic(state_path, data)
    return data


def _today_key(now_ts: float) -> str:
    return datetime.fromtimestamp(now_ts, tz=timezone.utc).strftime("%Y-%m-%d")


def record_session_snapshot(
    payload: StatusPayload,
    config_dir: Path | None = None,
    now_ts: float | None = None,
) -> tuple[int, float]:
    """Record current session tokens/cost and return (session_duration_sec, avg_daily_tokens).

    Tracks per-session monotonic token deltas so daily totals remain accurate
    even across multiple concurrent or resumed conversations.
    """
    now = time.time() if now_ts is None else now_ts
    stats_path = get_config_dir(config_dir) / STATS_FILENAME
    stats = read_json(stats_path, default={})
    if not isinstance(stats, dict):
        stats = {}

    sessions: dict[str, Any] = stats.setdefault("sessions", {})
    daily: dict[str, Any] = stats.setdefault("daily", {})

    conv_id = payload.conversation_id or payload.session_id
    total_in = payload.context_window.total_input_tokens
    total_out = payload.context_window.total_output_tokens
    total_tokens = total_in + total_out
    cost_usd = payload.cost.total_usd if payload.cost else 0.0

    duration_sec = 0
    if conv_id:
        prev = sessions.get(conv_id)
        if not isinstance(prev, dict):
            prev = {
                "started_at": now,
                "last_seen": now,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "model": "",
                "project": "",
            }
        prev_tokens = int(prev.get("input_tokens", 0)) + int(prev.get("output_tokens", 0))
        prev_cost = float(prev.get("cost_usd", 0.0))

        delta_tokens = max(0, total_tokens - prev_tokens)
        delta_cost = max(0.0, cost_usd - prev_cost)

        today = _today_key(now)
        day_entry = daily.get(today)
        if not isinstance(day_entry, dict):
            day_entry = {"tokens": 0, "cost_usd": 0.0, "sessions": 0}
        if conv_id not in sessions:
            day_entry["sessions"] = int(day_entry.get("sessions", 0)) + 1
        day_entry["tokens"] = int(day_entry.get("tokens", 0)) + delta_tokens
        day_entry["cost_usd"] = round(float(day_entry.get("cost_usd", 0.0)) + delta_cost, 6)
        daily[today] = day_entry

        started_at = float(prev.get("started_at", now))
        duration_sec = max(0, int(now - started_at))

        prev["last_seen"] = now
        prev["input_tokens"] = max(int(prev.get("input_tokens", 0)), total_in)
        prev["output_tokens"] = max(int(prev.get("output_tokens", 0)), total_out)
        prev["cost_usd"] = max(prev_cost, cost_usd)
        if payload.model and payload.model.display_name:
            prev["model"] = payload.model.display_name
        if payload.project_dir or payload.current_dir:
            prev["project"] = Path(payload.project_dir or payload.current_dir).name
        if payload.conversation_title:
            prev["title"] = payload.conversation_title
        sessions[conv_id] = prev

        _prune_old_entries(sessions, daily)
        write_json_atomic(stats_path, stats)

    avg_daily = compute_daily_burn_rate(daily, days=7)
    return duration_sec, avg_daily


def _prune_old_entries(sessions: dict[str, Any], daily: dict[str, Any]) -> None:
    if len(sessions) > MAX_STORED_SESSIONS:
        ordered = sorted(
            sessions.items(),
            key=lambda item: float(item[1].get("last_seen", 0)) if isinstance(item[1], dict) else 0.0,
            reverse=True,
        )
        sessions.clear()
        sessions.update(ordered[:MAX_STORED_SESSIONS])

    if len(daily) > MAX_STORED_DAYS:
        for key in sorted(daily.keys())[:-MAX_STORED_DAYS]:
            daily.pop(key, None)


def compute_daily_burn_rate(daily: dict[str, Any], days: int = 7) -> float:
    """Compute average tokens/day over the most recent `days` recorded days."""
    if not daily:
        return 0.0
    recent_keys = sorted(daily.keys())[-days:]
    values = [
        int(daily[k].get("tokens", 0))
        for k in recent_keys
        if isinstance(daily.get(k), dict) and int(daily[k].get("tokens", 0)) > 0
    ]
    if not values:
        return 0.0
    return sum(values) / len(values)
