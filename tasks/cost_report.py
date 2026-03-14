# TASK: Cost Report
# SCHEDULE: every day at 05:06
# ENABLED: false
# DESCRIPTION: Reads the AI usage log and sends a rolling 7-day cost summary to Telegram

"""
AI cost report task.

Reads data/usage.log, aggregates the last 7 days of API calls and tokens,
and sends a rolling summary message to your Telegram chat.

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


def _parse_line(line):
    """Parse a usage log line into a dict of key=value pairs."""
    parts = {}
    for segment in line.split("|"):
        for token in segment.strip().split():
            if "=" in token:
                k, v = token.split("=", 1)
                parts[k.strip()] = v.strip()
    return parts


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

    # Build per-day stats for the last 7 days
    today = date.today()
    days = [today - timedelta(days=i) for i in range(1, 8)]  # yesterday .. 7 days ago

    day_lines = {}
    for line in lines:
        day_str = line[:10]  # "YYYY-MM-DD"
        day_lines.setdefault(day_str, []).append(line)

    rows = []
    week_prompt = week_completion = week_calls = 0

    for d in days:
        d_str = str(d)
        bucket = day_lines.get(d_str, [])
        prompt = completion = 0
        for line in bucket:
            try:
                p = _parse_line(line)
                prompt     += int(p.get("prompt", 0))
                completion += int(p.get("completion", 0))
            except Exception:
                pass
        rows.append((d_str, len(bucket), prompt, completion))
        week_calls      += len(bucket)
        week_prompt     += prompt
        week_completion += completion

    week_total = week_prompt + week_completion
    # Rough cost estimate at $0.50 per million tokens
    week_cost = (week_total / 1_000_000) * 0.50

    # Build per-day lines (skip days with no activity)
    day_lines_out = []
    for d_str, calls, prompt, completion in rows:
        if calls == 0:
            continue
        total = prompt + completion
        cost  = (total / 1_000_000) * 0.50
        day_lines_out.append(
            f"  {d_str}: {calls} calls  {total:,} tok  ${cost:.4f}"
        )

    if not day_lines_out:
        day_section = "  (no activity in the last 7 days)"
    else:
        day_section = "\n".join(day_lines_out)

    message = (
        f"MolluskAI Cost Report — 7-day rolling\n"
        f"{'─' * 36}\n"
        f"{day_section}\n"
        f"{'─' * 36}\n"
        f"• 7-day total: {week_calls} calls  {week_total:,} tokens\n"
        f"  prompt: {week_prompt:,}  completion: {week_completion:,}\n"
        f"• Estimated cost: ${week_cost:.4f}\n"
        f"• Total log entries: {len(lines)}"
    )

    send(message)


if __name__ == "__main__":
    # Allow running this task directly for testing:  python tasks/daily_report.py
    run()
