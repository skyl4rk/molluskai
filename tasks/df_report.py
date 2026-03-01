# TASK: Disk Free Report (On Demand)
# SCHEDULE: on demand
# ENABLED: false
# DESCRIPTION: Sends full disk usage (df -h) to Telegram

import subprocess
from notify import send


def run():
    result = subprocess.run(["df", "-h"], capture_output=True, text=True)
    output = result.stdout or result.stderr or "No output from df."
    send(f"Disk usage:\n\n{output}")
