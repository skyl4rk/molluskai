# TASK: Diet Morning Report
# SCHEDULE: every day at 07:30
# ENABLED: false
# DESCRIPTION: Sends yesterday's food log and calorie total to Telegram

import sqlite3
import re
from datetime import datetime, timedelta
from pathlib import Path
from notify import send

DB_PATH = Path(__file__).parent.parent / "data" / "memory.db"


def run():
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            """
            SELECT content, timestamp
            FROM memories
            WHERE role = 'note'
              AND source = 'diet'
              AND DATE(timestamp) = ?
            ORDER BY timestamp
            """,
            (yesterday,),
        ).fetchall()
        conn.close()
    except Exception as e:
        print(f"[diet_report] DB error: {e}")
        return

    if not rows:
        return  # Nothing logged yesterday — no message sent

    total_kcal = 0
    lines = [f"Diet log for {yesterday}:\n"]

    for content, _ts in rows:
        lines.append(f"• {content.strip()}")
        match = re.search(r"~(\d+)\s*kcal", content, re.IGNORECASE)
        if match:
            total_kcal += int(match.group(1))

    lines.append(f"\nTotal: ~{total_kcal} kcal")
    send("\n".join(lines))
