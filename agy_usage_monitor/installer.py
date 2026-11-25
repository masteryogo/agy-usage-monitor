"""Safe installer and uninstaller for agy-usage-monitor."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

from agy_usage_monitor.state import (
    BACKUP_FILENAME,
    STATE_FILENAME,
    get_config_dir,
    is_dashboard_enabled,
    read_json,
    set_dashboard_enabled,
    write_json_atomic,
)

MARKER_COMMENT = "agy-usage-monitor"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _skills_target_dir(config_dir: Path) -> Path:
    # ~/.gemini/antigravity-cli -> ~/.gemini/config/skills
    return config_dir.parent / "config" / "skills"


def _launcher_command(config_dir: Path, is_windows: bool | None = None) -> str:
    win = (os.name == "nt") if is_windows is None else is_windows
    if win:
        cmd_path = str(config_dir / "statusline.cmd")
        return f'call "{cmd_path}"' if " " in cmd_path else cmd_path
    sh_path = (config_dir / "statusline.sh").as_posix()
    return sh_path


def _write_launchers(config_dir: Path, python_exe: str | None = None) -> None:
    py_exe = python_exe or sys.executable or "python"
    statusline_py = config_dir / "statusline.py"

    cmd_content = (
        f"@echo off\r\n"
        f"rem {MARKER_COMMENT} launcher\r\n"
        f'"{py_exe}" "{statusline_py}" %*\r\n'
    )
    (config_dir / "statusline.cmd").write_text(cmd_content, encoding="utf-8")

    sh_content = (
        f"#!/usr/bin/env sh\n# {MARKER_COMMENT} launcher\n"
        f'exec "{py_exe}" "{statusline_py.as_posix()}"\n'
    )
    sh_path = config_dir / "statusline.sh"
    sh_path.write_text(sh_content, encoding="utf-8")
    try:
        sh_path.chmod(0o755)
    except OSError:
        pass


def _is_our_statusline(status_cfg: Any) -> bool:
    if not isinstance(status_cfg, dict):
        return False
    cmd = str(status_cfg.get("command") or "")
    return any(name in cmd for name in ("statusline.cmd", "statusline.ps1", "statusline.sh", "statusline.py"))


def _backup_existing_path(src: Path, backup_dir: Path, name: str) -> bool:
    if not src.exists():
        return False
    backup_dir.mkdir(parents=True, exist_ok=True)
    dst = backup_dir / name
    if dst.exists():
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    return True


def _restore_backed_up_path(backup_dir: Path, dst: Path, name: str) -> None:
    src = backup_dir / name
    if not src.exists():
        return
    if dst.exists():
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)


def install(
    config_dir: Path | None = None,
    with_skills: bool = True,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Install agy-usage-monitor into Antigravity CLI config directory."""
    cfg = get_config_dir(config_dir)
    cfg.mkdir(parents=True, exist_ok=True)
    root = repo_root or _repo_root()

    settings_path = cfg / "settings.json"
    settings = read_json(settings_path, default={})
    if not isinstance(settings, dict):
        settings = {}

    backup_path = cfg / BACKUP_FILENAME
    backup_files_dir = cfg / ".agy-usage-monitor-backup"

    if not backup_path.exists():
        previous_statusline = settings.get("statusLine")
        backed_up_files: list[str] = []
        for fname in ("statusline.py", "statusline.cmd", "statusline.ps1", "statusline.sh", "agy_usage_monitor"):
            if _backup_existing_path(cfg / fname, backup_files_dir, fname):
                backed_up_files.append(fname)
        write_json_atomic(
            backup_path,
            {
                "had_statusLine": "statusLine" in settings,
                "statusLine": previous_statusline,
                "backed_up_files": backed_up_files,
            },
        )

    shutil.copy2(root / "scripts" / "statusline.py", cfg / "statusline.py")
    pkg_dst = cfg / "agy_usage_monitor"
    if pkg_dst.exists():
        shutil.rmtree(pkg_dst)
    shutil.copytree(
        root / "agy_usage_monitor",
        pkg_dst,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    _write_launchers(cfg)

    settings["statusLine"] = {
        "type": "command",
        "command": _launcher_command(cfg),
        "padding": 1,
        "enabled": True,
    }
    write_json_atomic(settings_path, settings)

    if not (cfg / STATE_FILENAME).exists():
        set_dashboard_enabled(True, config_dir=cfg)

    installed_skills: list[str] = []
    if with_skills:
        skills_src = root / "skills"
        skills_dst = _skills_target_dir(cfg)
        if skills_src.is_dir():
            for skill_folder in skills_src.iterdir():
                if skill_folder.is_dir():
                    target_name = f"agy-{skill_folder.name}"
                    target_path = skills_dst / target_name
                    if target_path.exists():
                        shutil.rmtree(target_path)
                    shutil.copytree(skill_folder, target_path)
                    installed_skills.append(target_name)

    return {
        "config_dir": str(cfg),
        "settings_path": str(settings_path),
        "command": settings["statusLine"]["command"],
        "skills": installed_skills,
    }


def uninstall(config_dir: Path | None = None, keep_skills: bool = False) -> dict[str, Any]:
    """Uninstall agy-usage-monitor and restore backed-up settings/files."""
    cfg = get_config_dir(config_dir)
    settings_path = cfg / "settings.json"
    settings = read_json(settings_path, default={})
    backup_path = cfg / BACKUP_FILENAME
    backup_files_dir = cfg / ".agy-usage-monitor-backup"
    backup = read_json(backup_path, default={}) if backup_path.exists() else {}

    if isinstance(settings, dict) and _is_our_statusline(settings.get("statusLine")):
        if isinstance(backup, dict) and backup.get("had_statusLine"):
            settings["statusLine"] = backup.get("statusLine")
        else:
            settings.pop("statusLine", None)
        write_json_atomic(settings_path, settings)

    for fname in ("statusline.py", "statusline.cmd", "statusline.ps1", "statusline.sh", STATE_FILENAME):
        target = cfg / fname
        if target.exists():
            target.unlink()

    pkg_dst = cfg / "agy_usage_monitor"
    if pkg_dst.exists():
        shutil.rmtree(pkg_dst)

    if isinstance(backup, dict):
        for fname in backup.get("backed_up_files", []):
            _restore_backed_up_path(backup_files_dir, cfg / fname, str(fname))

    if backup_path.exists():
        backup_path.unlink()
    if backup_files_dir.exists():
        shutil.rmtree(backup_files_dir)

    removed_skills: list[str] = []
    if not keep_skills:
        skills_dst = _skills_target_dir(cfg)
        for skill_name in ("agy-usage", "agy-dashboard"):
            spath = skills_dst / skill_name
            if spath.exists():
                shutil.rmtree(spath)
                removed_skills.append(skill_name)

    return {
        "config_dir": str(cfg),
        "restored_settings": settings_path.exists(),
        "removed_skills": removed_skills,
    }


def status_summary(config_dir: Path | None = None) -> dict[str, Any]:
    """Return current installation and dashboard status."""
    cfg = get_config_dir(config_dir)
    settings = read_json(cfg / "settings.json", default={})
    status_cfg = settings.get("statusLine") if isinstance(settings, dict) else None
    return {
        "config_dir": str(cfg),
        "installed": _is_our_statusline(status_cfg) and (cfg / "statusline.py").exists(),
        "dashboard_enabled": is_dashboard_enabled(cfg),
        "statusLine": status_cfg,
    }
