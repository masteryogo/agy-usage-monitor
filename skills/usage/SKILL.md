---
name: agy-usage
description: Show detailed Antigravity CLI token usage, estimated costs, daily breakdown, and 7-day burn rate from local stats.
---

# Antigravity Usage Report

Run the bundled usage report script and present the output clearly to the user:

```bash
python ~/.gemini/config/skills/agy-usage/scripts/usage_report.py
```

On Windows PowerShell:

```powershell
python "$env:USERPROFILE\.gemini\config\skills\agy-usage\scripts\usage_report.py"
```

If the user asks for more days (e.g., 14 or 30) or raw JSON, pass `--days <N>` or `--json`.
