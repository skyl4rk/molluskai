# TASK: CRM Calendar Scanner
# SCHEDULE: every day at 07:10
# ENABLED: false
# DESCRIPTION: Scans yesterday's events and next 7 days via khal vdir, adds attendees to CRM

import requests
import config
import crm
import calendar_client
from datetime import datetime, timedelta
from pathlib import Path


def run():
    if not Path(config.KHAL_CALENDAR_DIR).exists():
        print(f"[crm_calendar_scan] KHAL_CALENDAR_DIR not found ({config.KHAL_CALENDAR_DIR}) — skipping.")
        return

    crm.init()

    now       = datetime.now()
    yesterday = now - timedelta(days=1)
    next_week = now + timedelta(days=7)

    try:
        events = calendar_client.get_events(start=yesterday, end=next_week)
    except Exception as e:
        print(f"[crm_calendar_scan] calendar error: {e}")
        _send(f"CRM Calendar Scan failed: {e}")
        return

    added_contacts  = []
    interactions_logged = 0

    for event in events:
        attendees   = event.get("attendees", [])
        event_start = event.get("start")
        title       = event.get("title", "Unknown event")

        for email in attendees:
            email = email.lower().strip()
            if not email or email == config.EMAIL_IMAP_USER.lower():
                continue

            contact_id = _ensure_contact(email, title)
            if contact_id is None:
                continue

            # Determine past vs upcoming for interaction label
            if event_start and hasattr(event_start, "date"):
                is_past = event_start.date() < now.date()
            elif isinstance(event_start, datetime):
                is_past = event_start < now
            else:
                is_past = False

            summary = f"{'Attended' if is_past else 'Upcoming'}: {title}"
            crm.add_interaction(
                contact_id=contact_id,
                interaction_type="calendar_event",
                summary=summary,
                event_date=event_start if isinstance(event_start, datetime) else now,
                source="caldav_scan",
            )
            interactions_logged += 1

    if added_contacts or interactions_logged:
        lines = [f"CRM Calendar Scan — {now.strftime('%Y-%m-%d')}"]
        if added_contacts:
            lines.append(f"\nNew contacts from calendar ({len(added_contacts)}):")
            for c in added_contacts[:10]:
                lines.append(f"  + {c}")
        lines.append(f"\nInteractions logged: {interactions_logged}")
        _send("\n".join(lines))


def _ensure_contact(email: str, event_title: str):
    """
    Return existing contact_id or create a minimal contact from a calendar attendee.
    Returns None if the address is on the skip list.
    """
    existing = crm.get_contact(email=email)
    if existing:
        return existing["id"]

    if crm.is_skipped(email):
        return None

    contact_id = crm.add_contact(
        name=email.split("@")[0],
        email=email,
        notes=f"Auto-added from calendar event: {event_title}",
    )
    return contact_id


def _send(text: str) -> None:
    """Send a Telegram message via raw requests."""
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
            timeout=10,
        )
