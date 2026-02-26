# TASK: CRM Daily Summary
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: Updates relationship scores, generates contact nudges, sends Telegram report

import requests
import config
import crm
from datetime import datetime, date, timedelta


def run():
    crm.init()

    # Update relationship scores for all contacts
    conn = crm._connect()
    contact_ids = [row[0] for row in conn.execute("SELECT id FROM contacts").fetchall()]
    conn.close()

    for cid in contact_ids:
        crm.update_relationship_score(cid)

    stats         = crm.get_stats()
    neglected     = _get_neglected_contacts()
    due_followups = crm.get_pending_follow_ups(days_ahead=3)

    lines = [f"CRM Daily Summary — {date.today()}\n"]
    lines.append(f"Contacts:            {stats['total_contacts']}")
    lines.append(f"Interactions today:  {stats['interactions_today']}")
    lines.append(f"Pending follow-ups:  {stats['pending_follow_ups']}")
    lines.append(f"Pending proposals:   {stats['pending_proposals']}")

    if due_followups:
        lines.append(f"\nFollow-ups due (next 3 days): {len(due_followups)}")
        for fu in due_followups[:5]:
            lines.append(f"  • {fu['contact_name']} — due {fu['due_date']}")
            if fu.get("note"):
                lines.append(f"    {fu['note']}")

    if neglected:
        lines.append(f"\nNeglected contacts (no contact in 60+ days):")
        for c in neglected[:5]:
            last = (c.get("last_contact_date") or "never")
            score = c.get("relationship_score", 0)
            lines.append(f"  • {c['name']} — last: {last}  score: {score:.0f}")
        lines.append("Consider reaching out to these contacts.")

    _send("\n".join(lines))


def _get_neglected_contacts() -> list:
    """
    Return contacts with relationship_score < 20 and last contact > 60 days ago (or never).
    """
    cutoff = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    conn = crm._connect()
    rows = conn.execute(
        """
        SELECT id, name, email, last_contact_date, relationship_score
        FROM contacts
        WHERE relationship_score < 20
          AND (last_contact_date IS NULL OR last_contact_date < ?)
        ORDER BY relationship_score ASC
        LIMIT 10
        """,
        (cutoff,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _send(text: str) -> None:
    """Send a Telegram message via raw requests."""
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
            timeout=10,
        )
