# TASK: Expense Monthly Report
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: On the 1st of each month, sends last month's spending grouped by category to Telegram

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
    if today.day != 1:
        return  # Only run on the 1st of each month

    # Calculate last month's date range
    first_of_this_month = today.replace(day=1)
    last_month_end = first_of_this_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    month_label = last_month_start.strftime("%B %Y")

    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            """
            SELECT content
            FROM memories
            WHERE role = 'note'
              AND source = 'expenses'
              AND DATE(timestamp) >= ?
              AND DATE(timestamp) <= ?
            ORDER BY timestamp
            """,
            (last_month_start.strftime("%Y-%m-%d"), last_month_end.strftime("%Y-%m-%d")),
        ).fetchall()
        conn.close()
    except Exception as e:
        print(f"[expense_report] DB error: {e}")
        return

    if not rows:
        return  # Nothing logged last month — no message sent

    by_category = defaultdict(list)
    unmatched = []

    for (content,) in rows:
        # Expected format: YYYY-MM-DD HH:MM | category | description | amount
        parts = [p.strip() for p in content.split("|")]
        if len(parts) == 4:
            _dt, category, description, amount_str = parts
            amount_match = re.search(r"[\d.]+", amount_str)
            if amount_match:
                try:
                    amount = float(amount_match.group())
                    by_category[category].append((description, amount))
                    continue
                except ValueError:
                    pass
        unmatched.append(content.strip())

    # Build the message
    grand_total = 0.0
    lines = [f"Expenses — {month_label}\n"]

    for category in sorted(by_category):
        entries = by_category[category]
        cat_total = sum(amt for _, amt in entries)
        grand_total += cat_total
        lines.append(f"{category.title()}: {cat_total:.2f}")
        for desc, amt in entries:
            lines.append(f"  • {desc} — {amt:.2f}")

    lines.append(f"\nTotal: {grand_total:.2f}")

    if unmatched:
        lines.append(f"\n({len(unmatched)} entries could not be parsed)")

    _send("\n".join(lines))


def _send(text):
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
            timeout=10,
        )
