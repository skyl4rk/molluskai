# TASK: To-Do Reminder
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: Sends open to-do items to Telegram each morning

import requests
import config
import memory


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

    _send("\n".join(lines))


def _send(text: str) -> None:
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
            timeout=10,
        )
