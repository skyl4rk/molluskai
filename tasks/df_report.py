# TASK: Disk Free Report (On Demand)
# SCHEDULE: on demand
# ENABLED: false
# DESCRIPTION: Sends full disk usage (df -h) to Telegram

import subprocess
import requests
import config


def run():
    result = subprocess.run(["df", "-h"], capture_output=True, text=True)
    output = result.stdout or result.stderr or "No output from df."
    _send(f"Disk usage:\n\n{output}")


def _send(text):
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
            timeout=10,
        )
