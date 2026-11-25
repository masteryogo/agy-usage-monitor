"""Tests for agy_usage_monitor.dashboard."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from agy_usage_monitor.dashboard import format_duration, format_tokens, render_dashboard, strip_ansi
from agy_usage_monitor.models import StatusPayload


class TestDashboard(unittest.TestCase):
    def test_format_helpers(self) -> None:
        self.assertEqual(format_tokens(500), "500")
        self.assertEqual(format_tokens(84200), "84.2k")
        self.assertEqual(format_tokens(1_048_576), "1.0M")
        self.assertEqual(format_duration(45), "45s")
        self.assertEqual(format_duration(724), "12m04s")
        self.assertEqual(format_duration(8100), "2h15m")
        self.assertEqual(format_duration(90000), "1d01h")

    def test_render_full_dashboard_no_color(self) -> None:
        payload = StatusPayload.from_dict(
            {
                "workspace": {"project_dir": "/tmp/my-app"},
                "model": {"display_name": "Gemini 4 Argon (Medium)"},
                "vcs": {"type": "git"},
                "cycle_mode": "plan",
                "context_window": {
                    "total_input_tokens": 68500,
                    "total_output_tokens": 15700,
                    "context_window_size": 200000,
                    "used_percentage": 78.0,
                    "current_usage": {
                        "input_tokens": 8500,
                        "output_tokens": 1200,
                        "cache_read_input_tokens": 12300,
                    },
                },
                "quota": {
                    "gemini-5h": {"remaining_fraction": 0.52, "reset_in_seconds": 8100},
                    "gemini-weekly": {"remaining_fraction": 0.69, "reset_in_seconds": 172800},
                },
                "agent_state": "working",
                "subagents": [{"name": "s1", "role": "Tester", "status": "running"}],
                "task_count": 2,
                "cost": {"total_usd": 0.283, "estimated": False},
                "terminal_width": 120,
            }
        )
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            out = render_dashboard(payload, duration_sec=724, burn_rate_daily=45200)
        lines = out.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertIn("[Gemini 4 Argon (Medium)] my-app (git, plan)", lines[0])
        self.assertIn("[HIGH]", lines[0])
        self.assertIn("in/out: 68.5k/15.7k", lines[1])
        self.assertIn("cache~12.3k", lines[1])
        self.assertIn("agents:1 tasks:2", lines[1])
        self.assertIn("G:5h:", lines[2])
        self.assertIn("G:7d:", lines[2])
        self.assertIn("$0.283", lines[2])
        self.assertIn("12m04s", lines[2])
        self.assertIn("~45.2k/day", lines[2])

    def test_prioritizes_active_model_group_over_other_5h(self) -> None:
        payload = StatusPayload.from_dict(
            {
                "model": {"display_name": "Gemini 4 Hydrogen (Medium)"},
                "quota": {
                    "claude-5h": {"remaining_fraction": 1.0, "reset_in_seconds": 17940},
                    "gemini-5h": {"remaining_fraction": 0.9189, "reset_in_seconds": 15960},
                    "gemini-weekly": {"remaining_fraction": 0.9722, "reset_in_seconds": 602700},
                },
                "terminal_width": 120,
            }
        )
        out = strip_ansi(render_dashboard(payload))
        self.assertIn("G:5h:", out)
        self.assertIn("8%", out)
        self.assertIn("G:7d:", out)
        self.assertIn("3%", out)
        self.assertNotIn("C:5h:", out)

    def test_render_critical_badge_and_compact_mode(self) -> None:
        payload = StatusPayload.from_dict(
            {
                "cwd": "/tmp/app",
                "context_window": {"context_window_size": 100000, "used_percentage": 92.0},
                "terminal_width": 70,
            }
        )
        out = strip_ansi(render_dashboard(payload))
        self.assertIn("[CRIT]", out)
        self.assertIn("waiting for model response", out)


if __name__ == "__main__":
    unittest.main()
