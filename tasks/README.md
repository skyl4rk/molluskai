# Tasks

Tasks are Python scripts that run automatically on a schedule — **without making any AI API calls**. They are the cost-free automation layer of MolluskAI.

---

## How Tasks Work

Each task file begins with a metadata header block:

```python
# TASK: Name of the Task
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: What this task does
```

The agent's scheduler reads this header, parses the schedule, and runs the task at the right time. Tasks that are disabled (`ENABLED: false`) are discovered but not run.

---

## Enabling a Task

1. Open the task file in a text editor
2. Change `# ENABLED: false` to `# ENABLED: true`
3. Restart the agent (or run `systemctl --user restart molluskai` if using the service)

---

## Supported Schedule Strings

| String | Meaning |
|--------|---------|
| `every day at 08:00` | Once a day at 8am |
| `every hour` | Once per hour |
| `every 30 minutes` | Every 30 minutes |
| `every 10 seconds` | Every 10 seconds (useful for testing) |

---

## Writing a New Task

1. Copy `daily_report.py` as a template
2. Update the four metadata header lines
3. Write your logic in the `run()` function
4. Keep the `sys.path.insert` line so you can import project modules (e.g. `config`)

Tasks run in a background thread. Errors are printed to the console but do not crash the agent.

---

## System Actions

Tasks **can** use `subprocess` to perform system-level actions such as rebooting, moving files, or running shell commands. The AI itself cannot — only task scripts can.

Example reboot task:

```python
# TASK: Reboot Pi
# SCHEDULE: every day at 03:00
# ENABLED: false
# DESCRIPTION: Reboots the Raspberry Pi at 3am

import subprocess

def run():
    subprocess.run(["sudo", "reboot"])
```

Use system actions with care. Enable tasks only after reviewing the code.
