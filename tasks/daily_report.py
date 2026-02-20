# TASK: Daily Usage Report
# SCHEDULE: every day at 08:00
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

import os
import sys
from datetime import date
from pathlib import Path

# Add the project root to sys.path so we can import config and other modules
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))


def run():
    """Entry point called by the scheduler."""
    log_path = PROJECT_DIR / "data" / "usage.log"

    if not log_path.exists():
        _send("MolluskAI: No usage data recorded yet.")
        return

    lines = [l.strip() for l in log_path.read_text().splitlines() if l.strip()]
    if not lines:
        _send("MolluskAI: Usage log is empty.")
        return

    today       = str(date.today())
    today_lines = [l for l in lines if l.startswith(today)]

    total_prompt     = 0
    total_completion = 0

    for line in today_lines:
        # Format: "YYYY-MM-DD HH:MM:SS | model=... | prompt=N completion=N total=N"
        try:
            parts = {}
            for segment in line.split("|"):
                segment = segment.strip()
                if "=" in segment:
                    k, v = segment.split("=", 1)
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
        f"MolluskAI Daily Report — {today}\n"
        f"• Calls today: {calls}\n"
        f"• Tokens today: {total:,}  "
        f"(prompt: {total_prompt:,}  completion: {total_completion:,})\n"
        f"• Estimated cost today: ${estimated_cost:.4f}\n"
        f"• Total log entries: {len(lines)}"
    )

    _send(message)


def _send(text: str) -> None:
    """
    Send a message via the Telegram Bot API.
    Uses only the 'requests' library — no python-telegram-bot needed here.
    """
    import requests
    from dotenv import load_dotenv

    load_dotenv(PROJECT_DIR / ".env")
    token   = os.getenv("TELEGRAM_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        print(
            f"[daily_report] TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set in .env.\n"
            f"               Message would have been: {text}"
        )
        return

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        if not resp.ok:
            print(f"[daily_report] Telegram API error: {resp.text}")
    except Exception as e:
        print(f"[daily_report] Failed to send message: {e}")


if __name__ == "__main__":
    # Allow running this task directly for testing:  python tasks/daily_report.py
    run()
