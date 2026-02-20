# TASK: Workout Weekly Report
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: Every Monday, sends last week's workout summary to Telegram

import sqlite3
import re
import requests
import config
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent.parent / "data" / "memory.db"


def run():
    today = datetime.now()
    if today.weekday() != 0:
        return  # Only run on Monday

    # Last week: Monday to Sunday
    last_monday = (today - timedelta(days=7)).replace(hour=0, minute=0, second=0)
    last_sunday = (today - timedelta(days=1)).replace(hour=23, minute=59, second=59)
    week_label = f"{last_monday.strftime('%d %b')} – {last_sunday.strftime('%d %b %Y')}"

    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            """
            SELECT content, timestamp
            FROM memories
            WHERE role = 'note'
              AND source = 'workouts'
              AND DATE(timestamp) >= ?
              AND DATE(timestamp) <= ?
            ORDER BY timestamp
            """,
            (last_monday.strftime("%Y-%m-%d"), last_sunday.strftime("%Y-%m-%d")),
        ).fetchall()
        conn.close()
    except Exception as e:
        print(f"[workout_report] DB error: {e}")
        return

    if not rows:
        return  # No workouts logged last week — no message sent

    # Group by date and collect types
    by_date = defaultdict(list)
    type_counts = defaultdict(int)

    for content, ts in rows:
        parts = [p.strip() for p in content.split("|")]
        if len(parts) == 4:
            date_str = parts[0][:10]  # YYYY-MM-DD
            workout_type = parts[1]
            title = parts[2]
            details = parts[3]
            by_date[date_str].append((workout_type, title, details))
            type_counts[workout_type] += 1
        else:
            # Unparseable — show as-is under the date from the DB timestamp
            date_str = ts[:10]
            by_date[date_str].append(("", content.strip(), ""))

    days_trained = len(by_date)
    rest_days = 7 - days_trained

    lines = [f"Workouts — {week_label}"]
    lines.append(f"Trained: {days_trained}/7 days  •  Rest: {rest_days}\n")

    for date_str in sorted(by_date):
        day_label = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A %d %b")
        lines.append(f"{day_label}")
        for workout_type, title, details in by_date[date_str]:
            if workout_type:
                lines.append(f"  [{workout_type}] {title}")
                if details:
                    lines.append(f"  {details}")
            else:
                lines.append(f"  {title}")

    # Type summary
    if type_counts:
        lines.append("")
        summary_parts = [f"{t}: {n}" for t, n in sorted(type_counts.items())]
        lines.append("Session types: " + ", ".join(summary_parts))

    _send("\n".join(lines))


def _send(text):
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
            timeout=10,
        )
