"""Tests for agy_usage_monitor.installer."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agy_usage_monitor.cli import main as cli_main
from agy_usage_monitor.installer import install, status_summary, uninstall
from agy_usage_monitor.state import read_json, write_json_atomic


class TestInstaller(unittest.TestCase):
    def test_install_backup_and_uninstall_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cfg = base / ".gemini" / "antigravity-cli"
            cfg.mkdir(parents=True)

            original_settings = {
                "model": "Gemini 4 Hydrogen (Medium)",
                "statusLine": {"type": "command", "command": "custom.sh"},
            }
            write_json_atomic(cfg / "settings.json", original_settings)
            (cfg / "statusline.py").write_text("# old script\n", encoding="utf-8")

            res = install(config_dir=cfg, with_skills=True)
            self.assertTrue((cfg / "statusline.py").is_file())
            self.assertTrue((cfg / "statusline.cmd").is_file())
            self.assertTrue((cfg / "statusline.sh").is_file())
            self.assertTrue((cfg / "agy_usage_monitor" / "dashboard.py").is_file())
            self.assertEqual(sorted(res["skills"]), ["agy-dashboard", "agy-usage"])

            summary = status_summary(cfg)
            self.assertTrue(summary["installed"])
            self.assertTrue(summary["dashboard_enabled"])
            self.assertEqual(cli_main(["status", "--config-dir", str(cfg)]), 0)

            uninstall(config_dir=cfg, keep_skills=False)
            restored = read_json(cfg / "settings.json")
            self.assertEqual(restored["model"], "Gemini 4 Hydrogen (Medium)")
            self.assertEqual(restored["statusLine"], {"type": "command", "command": "custom.sh"})
            self.assertEqual((cfg / "statusline.py").read_text(encoding="utf-8"), "# old script\n")
            self.assertFalse((base / ".gemini" / "config" / "skills" / "agy-usage").exists())


if __name__ == "__main__":
    unittest.main()
