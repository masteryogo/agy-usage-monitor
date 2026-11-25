# agy-usage-monitor

Real-time usage dashboard for [Antigravity CLI (`agy`)](https://antigravity.google/docs/cli/statusline) in the terminal status line, inspired by `claude-usage-monitor`.

```text
[Gemini 4 Argon (Medium)] my-project (git, plan)  ctx ████░░░░░░░░░░ 28% (293.6k/1.0M)
  in/out: 88.2k/61.1k  last: 63.4k↑ 346↓  cache~20.9k  idle agents:1 tasks:1
  G:5h: █░░░░░░░ 8% rst 4h26m  G:7d: █░░░░░░░ 3% rst 6d23h  ~$0.421  4m12s  ~45.2k/day
```

## Features

- **Zero external dependencies** (pure Python 3.8+ standard library)
- **Context window meter** with color-coded progress bar and `[HIGH]` (75%) / `[CRIT]` (90%) badges
- **Token & cache breakdown** (session totals, last turn input/output, cache read/creation)
- **Quota buckets & reset countdown** (5h / 7d / custom buckets from `agy` statusLine payload)
- **Estimated cost, session duration & 7-day burn rate** tracked locally in `~/.gemini/antigravity-cli/agy-usage-stats.json`
- **Safe installer & uninstaller** with automatic backup of `~/.gemini/antigravity-cli/settings.json`
- **Antigravity skills** (`agy-usage` and `agy-dashboard`) for detailed reports and toggling the dashboard

## Install

### From GitHub

```powershell
git clone https://github.com/masteryogo/agy-usage-monitor.git
cd agy-usage-monitor
python install.py
```

### Via `uv` / `pip` (from GitHub)

```powershell
uv tool install git+https://github.com/masteryogo/agy-usage-monitor.git
agy-usage-monitor install
```

Restart `agy` (or run `/statusline enable` inside `agy`).

### Manage / Uninstall

```powershell
python install.py status
python install.py disable
python install.py enable
python install.py uninstall
```

### Usage Report

```powershell
python -m agy_usage_monitor.usage_report --days 7
```
