"""Tests for agy_usage_monitor.usage_report."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agy_usage_monitor.models import StatusPayload
from agy_usage_monitor.state import record_session_snapshot
from agy_usage_monitor.usage_report import build_usage_report


class TestUsageReport(unittest.TestCase):
    def test_report_includes_recorded_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp)
            payload = StatusPayload.from_dict(
                {
                    "conversation_id": "abc12345-dead-beef",
                    "workspace": {"project_dir": "/tmp/demo-proj"},
                    "model": {"display_name": "Gemini 4 Argon (Medium)"},
                    "context_window": {"total_input_tokens": 12000, "total_output_tokens": 3000},
                    "cost": {"total_usd": 0.15},
                }
            )
            record_session_snapshot(payload, config_dir=cfg, now_ts=1_700_000_000.0)
            report = build_usage_report(config_dir=cfg, days=7)
            self.assertIn("Antigravity Usage Report", report)
            self.assertIn("15.0k tokens", report)
            self.assertIn("demo-proj", report)
            self.assertIn("abc12345", report)


if __name__ == "__main__":
    unittest.main()
