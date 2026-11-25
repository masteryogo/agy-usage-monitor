"""Typed models for the Antigravity CLI statusLine JSON payload."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class ModelInfo:
    """Active model metadata."""

    id: str = ""
    display_name: str = ""
    effort: str = ""

    @classmethod
    def from_dict(cls, data: Any) -> ModelInfo | None:
        raw = _as_dict(data)
        if not raw:
            return None
        return cls(
            id=str(raw.get("id") or ""),
            display_name=str(raw.get("display_name") or raw.get("id") or ""),
            effort=str(raw.get("effort") or ""),
        )


@dataclass(frozen=True)
class CurrentUsage:
    """Token breakdown for the latest model turn."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    @classmethod
    def from_dict(cls, data: Any) -> CurrentUsage | None:
        raw = _as_dict(data)
        if not raw:
            return None
        return cls(
            input_tokens=_as_int(raw.get("input_tokens")),
            output_tokens=_as_int(raw.get("output_tokens")),
            cache_creation_input_tokens=_as_int(raw.get("cache_creation_input_tokens")),
            cache_read_input_tokens=_as_int(raw.get("cache_read_input_tokens")),
        )


@dataclass(frozen=True)
class ContextWindow:
    """Session context window usage metrics."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    context_window_size: int = 0
    used_percentage: float = 0.0
    remaining_percentage: float = 100.0
    current_usage: CurrentUsage | None = None

    @classmethod
    def from_dict(cls, data: Any) -> ContextWindow:
        raw = _as_dict(data)
        return cls(
            total_input_tokens=_as_int(raw.get("total_input_tokens")),
            total_output_tokens=_as_int(raw.get("total_output_tokens")),
            context_window_size=_as_int(raw.get("context_window_size")),
            used_percentage=_as_float(raw.get("used_percentage")),
            remaining_percentage=_as_float(raw.get("remaining_percentage"), 100.0),
            current_usage=CurrentUsage.from_dict(raw.get("current_usage")),
        )


@dataclass(frozen=True)
class QuotaBucket:
    """Quota status for a single Antigravity quota bucket."""

    bucket_id: str
    remaining_fraction: float | None = None
    remaining_amount: float | None = None
    reset_time: str = ""
    reset_in_seconds: int = 0
    disabled: bool = False

    @property
    def used_percentage(self) -> float | None:
        if self.remaining_fraction is None:
            return None
        clamped = max(0.0, min(1.0, self.remaining_fraction))
        return (1.0 - clamped) * 100.0

    @classmethod
    def from_dict(cls, bucket_id: str, data: Any) -> QuotaBucket:
        raw = _as_dict(data)
        rem_frac = raw.get("remaining_fraction")
        rem_amt = raw.get("remaining_amount")
        return cls(
            bucket_id=bucket_id,
            remaining_fraction=_as_float(rem_frac) if rem_frac is not None else None,
            remaining_amount=_as_float(rem_amt) if rem_amt is not None else None,
            reset_time=str(raw.get("reset_time") or ""),
            reset_in_seconds=_as_int(raw.get("reset_in_seconds")),
            disabled=bool(raw.get("disabled", False)),
        )


@dataclass(frozen=True)
class SubagentInfo:
    """Running or completed subagent summary."""

    name: str
    role: str = ""
    status: str = ""

    @classmethod
    def from_dict(cls, data: Any) -> SubagentInfo | None:
        raw = _as_dict(data)
        if not raw:
            return None
        return cls(
            name=str(raw.get("name") or ""),
            role=str(raw.get("role") or ""),
            status=str(raw.get("status") or ""),
        )


@dataclass(frozen=True)
class CostInfo:
    """Estimated session cost in USD."""

    total_usd: float = 0.0
    subagent_usd: float = 0.0
    estimated: bool = True

    @classmethod
    def from_dict(cls, data: Any) -> CostInfo | None:
        raw = _as_dict(data)
        if not raw:
            return None
        return cls(
            total_usd=_as_float(raw.get("total_usd")),
            subagent_usd=_as_float(raw.get("subagent_usd")),
            estimated=bool(raw.get("estimated", True)),
        )


@dataclass(frozen=True)
class StatusPayload:
    """Top-level JSON payload piped by Antigravity CLI to statusLine."""

    cwd: str = ""
    session_id: str = ""
    conversation_id: str = ""
    conversation_title: str = ""
    transcript_path: str = ""
    model: ModelInfo | None = None
    current_dir: str = ""
    project_dir: str = ""
    version: str = ""
    context_window: ContextWindow = field(default_factory=ContextWindow)
    exceeds_200k_tokens: bool = False
    product: str = "antigravity"
    quota: dict[str, QuotaBucket] = field(default_factory=dict)
    agent_state: str = ""
    vcs_type: str = ""
    cycle_mode: str = ""
    sandbox_enabled: bool = False
    subagents: tuple[SubagentInfo, ...] = ()
    artifact_count: int = 0
    plan_tier: str = ""
    email: str = ""
    pending_input_count: int = 0
    tool_confirmation_pending: bool = False
    task_count: int = 0
    terminal_width: int = 0
    cost: CostInfo | None = None

    @classmethod
    def from_dict(cls, data: Any) -> StatusPayload:
        raw = _as_dict(data)
        workspace = _as_dict(raw.get("workspace"))
        vcs = _as_dict(raw.get("vcs"))
        sandbox = _as_dict(raw.get("sandbox"))

        raw_quota = _as_dict(raw.get("quota"))
        quota = {
            str(k): QuotaBucket.from_dict(str(k), v)
            for k, v in raw_quota.items()
            if isinstance(v, dict)
        }

        raw_subagents = raw.get("subagents")
        subagents: list[SubagentInfo] = []
        if isinstance(raw_subagents, list):
            for item in raw_subagents:
                parsed = SubagentInfo.from_dict(item)
                if parsed is not None:
                    subagents.append(parsed)

        return cls(
            cwd=str(raw.get("cwd") or ""),
            session_id=str(raw.get("session_id") or ""),
            conversation_id=str(raw.get("conversation_id") or ""),
            conversation_title=str(raw.get("conversation_title") or ""),
            transcript_path=str(raw.get("transcript_path") or ""),
            model=ModelInfo.from_dict(raw.get("model")),
            current_dir=str(workspace.get("current_dir") or raw.get("cwd") or ""),
            project_dir=str(workspace.get("project_dir") or ""),
            version=str(raw.get("version") or ""),
            context_window=ContextWindow.from_dict(raw.get("context_window")),
            exceeds_200k_tokens=bool(raw.get("exceeds_200k_tokens") or False),
            product=str(raw.get("product") or "antigravity"),
            quota=quota,
            agent_state=str(raw.get("agent_state") or ""),
            vcs_type=str(vcs.get("type") or ""),
            cycle_mode=str(raw.get("cycle_mode") or ""),
            sandbox_enabled=bool(sandbox.get("enabled") or False),
            subagents=tuple(subagents),
            artifact_count=_as_int(raw.get("artifact_count")),
            plan_tier=str(raw.get("plan_tier") or ""),
            email=str(raw.get("email") or ""),
            pending_input_count=_as_int(raw.get("pending_input_count")),
            tool_confirmation_pending=bool(raw.get("tool_confirmation_pending") or False),
            task_count=_as_int(raw.get("task_count")),
            terminal_width=_as_int(raw.get("terminal_width")),
            cost=CostInfo.from_dict(raw.get("cost")),
        )
