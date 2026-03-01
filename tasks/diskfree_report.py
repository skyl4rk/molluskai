# TASK: Disk Free Report
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: Sends a Telegram alert if the main disk is over 75% full

import shutil
from notify import send

MOUNT_POINT    = "/"
ALERT_THRESHOLD = 75  # percent


def run():
    usage = shutil.disk_usage(MOUNT_POINT)
    percent_used = usage.used / usage.total * 100

    if percent_used < ALERT_THRESHOLD:
        return  # Disk fine — no message sent

    total_gb = usage.total / 1024 ** 3
    used_gb  = usage.used  / 1024 ** 3
    free_gb  = usage.free  / 1024 ** 3

    message = (
        f"Disk usage alert: {percent_used:.1f}% used\n"
        f"Used:  {used_gb:.1f} GB\n"
        f"Free:  {free_gb:.1f} GB\n"
        f"Total: {total_gb:.1f} GB\n"
        f"Mount: {MOUNT_POINT}"
    )
    send(message)
