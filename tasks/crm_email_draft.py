# TASK: CRM Email Draft Generator
# SCHEDULE: on demand
# ENABLED: false
# DESCRIPTION: Generates LLM-drafted email for a contact with two-phase Telegram approval

"""
This task has two modes:

1. 'run task: crm_email_draft' — shows status and usage instructions.

2. generate(contact_name, topic, reply_fn) — called by agent.py when the LLM
   detects a draft-email intent via the CRM skill. Not called by the scheduler.

Safety gate: CRM_EMAIL_DRAFT_ENABLED=true must be set in .env before drafts
can be created. The two-phase approval flow is handled by agent._pending_write.
"""

from typing import Optional

import requests
import config
import crm
import llm
from datetime import datetime


def run():
    """Called by 'run task: crm_email_draft' — prints status."""
    status = "ENABLED" if config.CRM_EMAIL_DRAFT_ENABLED else "DISABLED"
    msg = (
        f"CRM Email Draft Generator\n"
        f"Status: {status}\n"
        f"\n"
        f"To generate a draft:\n"
        f"  Tell the agent: 'draft email to <name> about <topic>'\n"
        f"\n"
        f"To enable drafting:\n"
        f"  Add CRM_EMAIL_DRAFT_ENABLED=true to .env"
    )
    _send(msg)
    print(msg)


def generate(contact_name: str, topic: str, reply_fn) -> Optional[dict]:
    """
    Generate an LLM email draft for a contact.

    Phase 1: Fetches CRM context, calls LLM, sends draft to user via reply_fn.
    Phase 2: Handled by agent._pending_write — user confirms with 'yes' to send.

    Returns a pending dict for agent._pending_write, or None on error.
    Safety gate: CRM_EMAIL_DRAFT_ENABLED must be True.
    """
    if not config.CRM_EMAIL_DRAFT_ENABLED:
        reply_fn(
            "CRM email drafting is disabled.\n"
            "Set CRM_EMAIL_DRAFT_ENABLED=true in .env to enable it."
        )
        return None

    # Look up the contact
    contacts = crm.search_contacts(contact_name, n=1)
    if not contacts:
        reply_fn(
            f"No contact found matching '{contact_name}'.\n"
            f"Try: tell agent 'find contact {contact_name}'"
        )
        return None

    contact        = contacts[0]
    contact_id     = contact["id"]
    context_chunks = crm.get_contact_context(contact_id, query=topic, n=5)
    interactions   = _get_recent_interactions(contact_id, n=10)

    context_text = "\n".join(c["content"] for c in context_chunks)
    interaction_text = "\n".join(
        f"- {i.get('event_date', '')[:10]}: {i.get('type', '')} — {i.get('summary', '')}"
        for i in interactions
    )

    messages = [{
        "role": "user",
        "content": (
            f"Draft a professional email to {contact['name']} "
            f"({contact.get('email', 'no email on file')}) "
            f"about: {topic}\n\n"
            f"Context about this person:\n{context_text or 'No context stored yet.'}\n\n"
            f"Recent interactions:\n{interaction_text or 'No interactions recorded yet.'}\n\n"
            f"Write only the email body. Be concise and warm. No subject line."
        ),
    }]

    try:
        draft = llm.chat(messages, "You are a professional email writer.")
    except Exception as e:
        reply_fn(f"LLM error generating draft: {e}")
        return None

    reply_fn(
        f"Draft email to {contact['name']} <{contact.get('email', '')}>:\n"
        f"{'─' * 40}\n"
        f"{draft}\n"
        f"{'─' * 40}\n"
        f"Reply yes to send, no to cancel."
    )

    return {
        "type":       "email_draft",
        "to":         contact.get("email", ""),
        "contact_id": contact_id,
        "content":    draft,
        "topic":      topic,
    }


def _get_recent_interactions(contact_id: int, n: int = 10) -> list:
    conn = crm._connect()
    rows = conn.execute(
        "SELECT type, summary, event_date FROM interactions "
        "WHERE contact_id = ? ORDER BY event_date DESC LIMIT ?",
        (contact_id, n),
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


