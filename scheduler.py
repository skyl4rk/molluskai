# scheduler.py — Discover and run Tasks from the tasks/ directory
#
# Tasks are Python scripts in tasks/*.py with a metadata header block.
# The scheduler reads the header, registers enabled tasks with the
# 'schedule' library, and runs them in a background daemon thread.
#
# Task metadata header format (at the top of the .py file):
#
#   # TASK: Daily Report
#   # SCHEDULE: every day at 08:00
#   # ENABLED: false
#   # DESCRIPTION: Sends a daily usage summary to Telegram
#
# Supported SCHEDULE strings:
#   every day at HH:MM    (e.g. every day at 08:00)
#   every hour
#   every N minutes       (e.g. every 30 minutes)
#   every N seconds       (useful for testing)

import importlib.util
import threading
import time
from pathlib import Path

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    schedule = None
    SCHEDULE_AVAILABLE = False

TASKS_DIR = Path(__file__).parent / "tasks"


def discover_tasks() -> list:
    """
    Scan tasks/*.py and parse their metadata header.
    Returns a list of dicts, each with keys:
        name, schedule, enabled, description, path
    """
    tasks = []
    for path in sorted(TASKS_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue  # skip __init__.py and private files

        meta = {
            "name":        path.stem,
            "schedule":    None,
            "enabled":     False,
            "description": "",
            "path":        path,
        }

        try:
            with open(path) as f:
                for line in f:
                    stripped = line.strip()
                    # Stop reading once we leave the header comment block
                    if stripped and not stripped.startswith("#"):
                        break
                    # Parse metadata keys
                    upper = stripped.upper()
                    if upper.startswith("# TASK:"):
                        meta["name"] = stripped[7:].strip()
                    elif upper.startswith("# SCHEDULE:"):
                        meta["schedule"] = stripped[11:].strip()
                    elif upper.startswith("# ENABLED:"):
                        meta["enabled"] = stripped[10:].strip().lower() == "true"
                    elif upper.startswith("# DESCRIPTION:"):
                        meta["description"] = stripped[14:].strip()
        except Exception as e:
            print(f"[scheduler] Could not read {path.name}: {e}")

        tasks.append(meta)
    return tasks


def _run_task(path: Path) -> None:
    """
    Load a task script and call its run() function.
    Errors are caught so a broken task doesn't crash the scheduler.
    """
    import sys
    # Ensure the project root is on sys.path so tasks can import config etc.
    # Tasks do not need to add this themselves.
    project_root = str(path.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    spec   = importlib.util.spec_from_file_location("task_module", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        if hasattr(module, "run"):
            module.run()
        else:
            print(f"[scheduler] {path.name} has no run() function — skipping.")
    except Exception as e:
        print(f"[scheduler] Error in task '{path.name}': {e}")


def _register(task: dict) -> bool:
    """
    Register a task with the schedule library.
    Returns True on success, False if the schedule string is unrecognised.
    """
    s    = task["schedule"].lower().strip()
    path = task["path"]
    name = task["name"]

    try:
        if "every day at" in s:
            time_str = s.split("at")[-1].strip()
            schedule.every().day.at(time_str).do(_run_task, path)

        elif s == "every hour":
            schedule.every().hour.do(_run_task, path)

        elif "every" in s and "hour" in s:
            # e.g. "every 2 hours"
            n = int("".join(c for c in s if c.isdigit()) or "1")
            schedule.every(n).hours.do(_run_task, path)

        elif "every" in s and "minute" in s:
            n = int("".join(c for c in s if c.isdigit()) or "1")
            schedule.every(n).minutes.do(_run_task, path)

        elif "every" in s and "second" in s:
            n = int("".join(c for c in s if c.isdigit()) or "1")
            schedule.every(n).seconds.do(_run_task, path)

        else:
            print(f"[scheduler] Unrecognised schedule for '{name}': {s}")
            return False

        print(f"[scheduler] Scheduled '{name}': {s}")
        return True

    except Exception as e:
        print(f"[scheduler] Failed to register '{name}': {e}")
        return False


def _load_tasks() -> None:
    """Discover enabled tasks and register them with the schedule library."""
    tasks   = discover_tasks()
    enabled = [t for t in tasks if t["enabled"] and t["schedule"]]

    if not enabled:
        print(f"[scheduler] {len(tasks)} task(s) found, none enabled.")
    else:
        registered = sum(1 for t in enabled if _register(t))
        print(f"[scheduler] {registered}/{len(enabled)} task(s) registered.")


def start() -> None:
    """
    Discover enabled tasks, register them, and start the scheduler loop
    in a background daemon thread. Returns immediately.
    """
    if not SCHEDULE_AVAILABLE:
        print("[scheduler] 'schedule' library not installed — tasks disabled. Run: pip install schedule")
        return

    _load_tasks()

    def _loop():
        while True:
            schedule.run_pending()
            time.sleep(10)

    thread = threading.Thread(target=_loop, daemon=True, name="scheduler")
    thread.start()


def reload() -> None:
    """
    Re-discover tasks and re-register them without restarting the agent.
    Called after enable task: / disable task: commands.
    """
    if not SCHEDULE_AVAILABLE:
        return
    schedule.clear()
    _load_tasks()
