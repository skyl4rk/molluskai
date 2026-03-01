# TASK: To-Do Reminder
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: Sends open to-do items to Telegram each morning

import memory
from notify import send


def run():
    memory.init()
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
