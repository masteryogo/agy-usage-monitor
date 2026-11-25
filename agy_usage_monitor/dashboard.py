"""ANSI terminal dashboard renderer for Antigravity CLI statusLine."""

from __future__ import annotations

import os
import re
from pathlib import Path

from agy_usage_monitor.models import QuotaBucket, StatusPayload

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences to measure visible character width."""
    return ANSI_RE.sub("", text)


def format_tokens(count: int | float) -> str:
    """Format token counts compactly (e.g. 84.2k, 1.0M)."""
    value = float(count)
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(int(round(value)))


def format_duration(seconds: int) -> str:
    """Format elapsed or countdown seconds (e.g. 2h15m, 12m04s, 45s)."""
    secs = max(0, int(seconds))
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days > 0:
        return f"{days}d{hours:02d}h"
    if hours > 0:
        return f"{hours}h{minutes:02d}m"
    if minutes > 0:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def color_for_percent(pct: float) -> str:
    """Return ANSI color code based on usage percentage thresholds."""
    if pct >= 90.0:
        return RED
    if pct >= 75.0:
        return YELLOW
    return GREEN


def render_bar(pct: float, width: int = 12) -> str:
    """Render a color-coded Unicode progress bar."""
    clamped = max(0.0, min(100.0, pct))
    filled = int(round((clamped / 100.0) * width))
    empty = max(0, width - filled)
    color = color_for_percent(clamped)
    return f"{color}{'█' * filled}{DIM}{'░' * empty}{RESET}"


def _short_model_name(payload: StatusPayload) -> str:
    if not payload.model or not payload.model.display_name:
        return "Antigravity"
    return payload.model.display_name


def _project_label(payload: StatusPayload) -> str:
    raw = payload.project_dir or payload.current_dir or payload.cwd
    if not raw:
        return "~"
    name = Path(raw).name
    return name or raw


def _bucket_group_and_period(bucket_id: str) -> tuple[str, str]:
    name = bucket_id.lower()
    group = ""
    if "gemini" in name:
        group = "G"
    elif any(tok in name for tok in ("claude", "anthropic", "gpt", "third")):
        group = "C"

    if "5h" in name or "five" in name or "hour" in name:
        period = "5h"
    elif "7d" in name or "week" in name:
        period = "7d"
    else:
        period = bucket_id[:10]
    return group, period


def _shorten_bucket_name(bucket_id: str) -> str:
    group, period = _bucket_group_and_period(bucket_id)
    return f"{group}:{period}" if group else period


def _active_model_group(payload: StatusPayload) -> str:
    name = (payload.model.display_name if payload.model else "").lower()
    if any(tok in name for tok in ("claude", "gpt", "opus", "sonnet")):
        return "C"
    if "gemini" in name or "orchestrator" in name:
        return "G"
    return ""


def _sort_buckets(buckets: dict[str, QuotaBucket], active_group: str = "") -> list[QuotaBucket]:
    def key_fn(bucket: QuotaBucket) -> tuple[int, int, str]:
        group, period = _bucket_group_and_period(bucket.bucket_id)
        group_rank = 0 if (active_group and group == active_group) else (1 if group else 2)
        period_rank = 0 if period == "5h" else (1 if period == "7d" else 2)
        return (group_rank, period_rank, bucket.bucket_id)

    return sorted(buckets.values(), key=key_fn)


def _format_quota_segment(bucket: QuotaBucket) -> str:
    label = _shorten_bucket_name(bucket.bucket_id)
    if bucket.disabled:
        return f"{label}: {DIM}off{RESET}"
    used = bucket.used_percentage
    if used is not None:
        color = color_for_percent(used)
        bar = render_bar(used, width=8)
        reset_txt = f" {DIM}rst {format_duration(bucket.reset_in_seconds)}{RESET}" if bucket.reset_in_seconds > 0 else ""
        return f"{label}: {bar} {color}{used:.0f}%{RESET}{reset_txt}"
    if bucket.remaining_amount is not None:
        return f"{label}: {CYAN}{bucket.remaining_amount:g}{RESET}"
    return f"{label}: {DIM}--{RESET}"


def _render_line1(payload: StatusPayload, compact: bool) -> str:
    model_name = _short_model_name(payload)
    project = _project_label(payload)

    meta_parts: list[str] = []
    if payload.vcs_type:
        meta_parts.append(payload.vcs_type)
    if payload.cycle_mode:
        meta_parts.append(payload.cycle_mode)
    if payload.sandbox_enabled:
        meta_parts.append("sandbox")
    meta = f" {DIM}({', '.join(meta_parts)}){RESET}" if meta_parts else ""

    ctx = payload.context_window
    bar_width = 8 if compact else 14
    if ctx.context_window_size > 0:
        used_pct = ctx.used_percentage
        used_tokens = int(round((used_pct / 100.0) * ctx.context_window_size))
        pct_color = color_for_percent(used_pct)
        ctx_str = (
            f"ctx {render_bar(used_pct, width=bar_width)} "
            f"{pct_color}{used_pct:.0f}%{RESET} "
            f"{DIM}({format_tokens(used_tokens)}/{format_tokens(ctx.context_window_size)}){RESET}"
        )
        if used_pct >= 90.0:
            ctx_str += f" {RED}{BOLD}[CRIT]{RESET}"
        elif used_pct >= 75.0:
            ctx_str += f" {YELLOW}{BOLD}[HIGH]{RESET}"
    else:
        ctx_str = f"ctx {DIM}...{RESET}"

    return f"{CYAN}{BOLD}[{model_name}]{RESET} {WHITE}{project}{RESET}{meta}  {ctx_str}"


def _render_line2(payload: StatusPayload, compact: bool) -> str:
    ctx = payload.context_window
    in_tok = format_tokens(ctx.total_input_tokens)
    out_tok = format_tokens(ctx.total_output_tokens)
    parts = [f"in/out: {WHITE}{in_tok}/{out_tok}{RESET}"]

    if ctx.current_usage is not None:
        cur = ctx.current_usage
        parts.append(
            f"last: {CYAN}{format_tokens(cur.input_tokens)}↑{RESET} "
            f"{MAGENTA}{format_tokens(cur.output_tokens)}↓{RESET}"
        )
        if cur.cache_read_input_tokens > 0 or cur.cache_creation_input_tokens > 0:
            cache_bits: list[str] = []
            if cur.cache_creation_input_tokens > 0:
                cache_bits.append(f"cache+{format_tokens(cur.cache_creation_input_tokens)}")
            if cur.cache_read_input_tokens > 0:
                cache_bits.append(f"cache~{format_tokens(cur.cache_read_input_tokens)}")
            parts.append(f"{DIM}{' '.join(cache_bits)}{RESET}")

    if not compact:
        extras: list[str] = []
        if payload.agent_state:
            state_color = YELLOW if payload.agent_state in {"working", "tool_use", "reviewing"} else GREEN
            if payload.agent_state == "error":
                state_color = RED
            extras.append(f"{state_color}{payload.agent_state}{RESET}")
        running_subs = sum(1 for s in payload.subagents if s.status == "running")
        if running_subs > 0:
            extras.append(f"{MAGENTA}agents:{running_subs}{RESET}")
        if payload.task_count > 0:
            extras.append(f"{BLUE}tasks:{payload.task_count}{RESET}")
        if payload.artifact_count > 0:
            extras.append(f"{DIM}artifacts:{payload.artifact_count}{RESET}")
        if extras:
            parts.append(" ".join(extras))

    return "  " + "  ".join(parts)


def _render_line3(
    payload: StatusPayload,
    duration_sec: int,
    burn_rate_daily: float,
    compact: bool,
) -> str:
    parts: list[str] = []

    if payload.quota:
        buckets = _sort_buckets(payload.quota, active_group=_active_model_group(payload))
        limit = 1 if compact else 2
        for bucket in buckets[:limit]:
            parts.append(_format_quota_segment(bucket))

    if payload.cost is not None:
        prefix = "~$" if payload.cost.estimated else "$"
        parts.append(f"{GREEN}{prefix}{payload.cost.total_usd:.3f}{RESET}")

    if duration_sec > 0:
        parts.append(f"{DIM}{format_duration(duration_sec)}{RESET}")

    if burn_rate_daily > 0 and not compact:
        parts.append(f"{DIM}~{format_tokens(burn_rate_daily)}/day{RESET}")

    if not parts:
        tier = f" ({payload.plan_tier})" if payload.plan_tier else ""
        return f"  {DIM}waiting for model response{tier}...{RESET}"

    return "  " + "  ".join(parts)


def render_dashboard(
    payload: StatusPayload,
    duration_sec: int = 0,
    burn_rate_daily: float = 0.0,
) -> str:
    """Render the 3-line Antigravity statusLine dashboard."""
    if os.environ.get("NO_COLOR"):
        return strip_ansi(
            "\n".join(
                [
                    _render_line1(payload, compact=False),
                    _render_line2(payload, compact=False),
                    _render_line3(payload, duration_sec, burn_rate_daily, compact=False),
                ]
            )
        )

    compact = 0 < payload.terminal_width < 88
    lines = [
        _render_line1(payload, compact=compact),
        _render_line2(payload, compact=compact),
        _render_line3(payload, duration_sec, burn_rate_daily, compact=compact),
    ]
    return "\n".join(lines)
