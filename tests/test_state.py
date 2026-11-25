"""Tests for agy_usage_monitor.state and statusline."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agy_usage_monitor.models import StatusPayload
from agy_usage_monitor.state import (
    STATS_FILENAME,
    is_dashboard_enabled,
    read_json,
    record_session_snapshot,
    set_dashboard_enabled,
)
from agy_usage_monitor.statusline import process_stdin


class TestState(unittest.TestCase):
    def test_dashboard_toggle_and_process_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp)
            self.assertTrue(is_dashboard_enabled(cfg))
            set_dashboard_enabled(False, cfg)
            self.assertFalse(is_dashboard_enabled(cfg))

            sample = json.dumps({"conversation_id": "c1", "cwd": "/tmp/p"})
            self.assertEqual(process_stdin(sample, config_dir=cfg), "")

            set_dashboard_enabled(True, cfg)
            rendered = process_stdin(sample, config_dir=cfg)
            self.assertIn("Antigravity", rendered)

    def test_monotonic_session_deltas_and_burn_rate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp)
            p1 = StatusPayload.from_dict(
                {
                    "conversation_id": "c1",
                    "context_window": {"total_input_tokens": 1000, "total_output_tokens": 500},
                    "cost": {"total_usd": 0.05},
                }
            )
            dur1, avg1 = record_session_snapshot(p1, config_dir=cfg, now_ts=1_700_000_000.0)
            self.assertEqual(dur1, 0)
            self.assertEqual(avg1, 1500.0)

            p2 = StatusPayload.from_dict(
                {
                    "conversation_id": "c1",
                    "context_window": {"total_input_tokens": 2000, "total_output_tokens": 1000},
                    "cost": {"total_usd": 0.12},
                }
            )
            dur2, avg2 = record_session_snapshot(p2, config_dir=cfg, now_ts=1_700_000_120.0)
            self.assertEqual(dur2, 120)
            self.assertEqual(avg2, 3000.0)

            stats = read_json(cfg / STATS_FILENAME)
            day_key = next(iter(stats["daily"]))
            self.assertEqual(stats["daily"][day_key]["tokens"], 3000)
            self.assertEqual(stats["daily"][day_key]["sessions"], 1)


if __name__ == "__main__":
    unittest.main()
