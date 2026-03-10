# TASK: Daily Usage Report
# SCHEDULE: every day at 05:06
# ENABLED: false
# DESCRIPTION: Reads the AI usage log and sends a brief daily summary to Telegram

"""
Daily AI usage report task.

Reads data/usage.log, counts today's API calls and tokens, and sends
a short summary message to your Telegram chat.

To enable this task:
  1. Set  # ENABLED: true  in the header above
  2. Add  TELEGRAM_CHAT_ID=<your_chat_id>  to .env
     (Your chat ID is usually the same as your Telegram user ID.
      Find it by messaging @userinfobot on Telegram.)
  3. Restart the agent

This task uses NO AI credits — it reads the log file and sends
a pre-formatted message directly via the Telegram Bot API.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

# Add the project root to sys.path so we can import config and other modules
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from notify import send


def run():
    """Entry point called by the scheduler."""
    log_path = PROJECT_DIR / "data" / "usage.log"

    if not log_path.exists():
        send("MolluskAI: No usage data recorded yet.")
        return

    lines = [l.strip() for l in log_path.read_text().splitlines() if l.strip()]
    if not lines:
        send("MolluskAI: Usage log is empty.")
        return

    yesterday       = str(date.today() - timedelta(days=1))
    today_lines     = [l for l in lines if l.startswith(yesterday)]

    total_prompt     = 0
    total_completion = 0

    for line in today_lines:
        # Format: "YYYY-MM-DD HH:MM:SS | model=... | prompt=N completion=N total=N"
        try:
            parts = {}
            for segment in line.split("|"):
                for token in segment.strip().split():
                    if "=" in token:
                        k, v = token.split("=", 1)
                        parts[k.strip()] = v.strip()
            total_prompt     += int(parts.get("prompt", 0))
            total_completion += int(parts.get("completion", 0))
        except Exception:
            pass

    total = total_prompt + total_completion
    calls = len(today_lines)

    # Rough cost estimate at $0.50 per million tokens
    estimated_cost = (total / 1_000_000) * 0.50

    message = (
        f"MolluskAI Daily Report — {yesterday}\n"
        f"• Calls today: {calls}\n"
        f"• Tokens today: {total:,}  "
        f"(prompt: {total_prompt:,}  completion: {total_completion:,})\n"
        f"• Estimated cost today: ${estimated_cost:.4f}\n"
        f"• Total log entries: {len(lines)}"
    )

    send(message)


if __name__ == "__main__":
    # Allow running this task directly for testing:  python tasks/daily_report.py
    run()
