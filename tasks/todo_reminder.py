# TASK: To-Do Reminder
# SCHEDULE: every day at 05:00
# ENABLED: false
# DESCRIPTION: Sends open to-do items to Telegram each morning; removes done items older than 1 day

import memory
from notify import send


def run():
    # Remove done items completed more than 24 hours ago
    memory.cleanup_done_notes("todo", older_than_hours=24)

    # Report remaining open items
    notes = memory.get_notes("todo")
    open_items = [
        n["content"].strip()
        for n in notes
        if n["content"].strip().startswith("[ ]")
    ]

    if not open_items:
        return  # nothing to report

    lines = [f"To-Do ({len(open_items)} open):"]
    for item in open_items:
        lines.append(f"  {item}")

    send("\n".join(lines))
