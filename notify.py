# notify.py — shared notification utility for tasks
#
# Sends task output to both the terminal (stdout) and Telegram (if configured).
# Import and use in task scripts instead of a local _send() function:
#
#   from notify import send
#   send("Hello from my task")

import requests
import config


def send(text: str) -> None:
    """Print to terminal and send to Telegram (if configured)."""
    print(f"\n[task] {text}\n")
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
                timeout=10,
            )
        except Exception as e:
            print(f"[notify] Telegram error: {e}")
