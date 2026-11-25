"""Tests for agy_usage_monitor.models."""

from __future__ import annotations

import unittest

from agy_usage_monitor.models import QuotaBucket, StatusPayload


class TestModels(unittest.TestCase):
    def test_parses_official_sample_payload(self) -> None:
        raw = {
            "cwd": "/home/user/my-project",
            "session_id": "conv-1",
            "conversation_id": "conv-1",
            "conversation_title": "Explain factorial",
            "model": {
                "id": "Gemini 4 Argon (Medium)",
                "display_name": "Gemini 4 Argon (Medium)",
                "effort": "medium",
            },
            "workspace": {"current_dir": "/home/user/my-project", "project_dir": "/home/user/my-project"},
            "context_window": {
                "total_input_tokens": 88244,
                "total_output_tokens": 61074,
                "context_window_size": 1048576,
                "used_percentage": 14.24,
                "remaining_percentage": 85.76,
                "current_usage": {
                    "input_tokens": 63382,
                    "output_tokens": 346,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 20857,
                },
            },
            "quota": {
                "gemini-weekly": {
                    "remaining_fraction": 0.9378,
                    "reset_time": "2026-07-06T07:50:32Z",
                    "reset_in_seconds": 560580,
                }
            },
            "agent_state": "idle",
            "vcs": {"type": "git"},
            "cycle_mode": "plan",
            "sandbox": {"enabled": False},
            "subagents": [{"name": "research-1", "role": "Researcher", "status": "running"}],
            "artifact_count": 2,
            "task_count": 1,
            "terminal_width": 111,
            "cost": {"total_usd": 0.4213, "subagent_usd": 0, "estimated": False},
        }
        payload = StatusPayload.from_dict(raw)
        self.assertEqual(payload.model.display_name, "Gemini 4 Argon (Medium)")
        self.assertEqual(payload.vcs_type, "git")
        self.assertEqual(payload.cycle_mode, "plan")
        self.assertEqual(payload.context_window.total_input_tokens, 88244)
        self.assertIsNotNone(payload.context_window.current_usage)
        self.assertEqual(payload.context_window.current_usage.cache_read_input_tokens, 20857)
        self.assertEqual(len(payload.subagents), 1)
        self.assertAlmostEqual(payload.cost.total_usd, 0.4213)
        self.assertAlmostEqual(payload.quota["gemini-weekly"].used_percentage or 0.0, 6.22, places=2)

    def test_handles_empty_and_malformed_payload(self) -> None:
        payload = StatusPayload.from_dict(None)
        self.assertIsNone(payload.model)
        self.assertEqual(payload.context_window.context_window_size, 0)
        self.assertEqual(payload.quota, {})

    def test_quota_clamps_fraction(self) -> None:
        b = QuotaBucket.from_dict("test", {"remaining_fraction": 1.5})
        self.assertEqual(b.used_percentage, 0.0)
        b2 = QuotaBucket.from_dict("test", {"remaining_fraction": -0.2})
        self.assertEqual(b2.used_percentage, 100.0)


if __name__ == "__main__":
    unittest.main()
