# TASK: CRM Email Contact Scanner
# SCHEDULE: every day at 07:00
# ENABLED: false
# DESCRIPTION: Scans last 24h of INBOX via IMAP, proposes new contacts via Telegram

import imaplib
import email as _email
import requests
import config
import crm
from datetime import datetime, timedelta
from email.header import decode_header as _decode_header
from email.utils import getaddresses
from pathlib import Path


def run():
    if not config.EMAIL_IMAP_HOST:
        print("[crm_email_scan] EMAIL_IMAP_HOST not set — skipping.")
        return

    crm.init()

    addresses = _scan_inbox_24h()
    if not addresses:
        return

    new_proposals = []
    auto_added    = []
    skipped       = 0

    for addr_email, addr_name in addresses:
        # Skip if already a known contact — just log the interaction
        existing = crm.get_contact(email=addr_email)
        if existing:
            crm.add_interaction(
                contact_id=existing["id"],
                interaction_type="email_in",
                summary="Email detected by daily scan",
                event_date=datetime.now(),
                source="imap_scan",
            )
            continue

        # Skip if matches skip_patterns or config.CRM_SKIP_DOMAINS
        if crm.is_skipped(addr_email):
            skipped += 1
            continue

        # Track as a proposal (increments seen_count on repeat appearances)
        proposal = crm.get_or_create_proposal(addr_email, addr_name)

        if config.CRM_AUTO_ADD_MODE and proposal["seen_count"] >= 50:
            contact_id = crm.approve_proposal(addr_email)
            display_name = f"{addr_name} <{addr_email}>" if addr_name else addr_email
            auto_added.append(display_name)
        else:
            new_proposals.append(proposal)

    _send_report(new_proposals, auto_added, skipped)


def _scan_inbox_24h() -> list:
    """
    Connect via IMAP, search last 24h of INBOX, extract unique sender/recipient addresses.
    Returns list of (email_address, display_name) tuples. Skips large threads (>= 10 addrs).
    """
    addresses = {}
    since_date = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")

    try:
        mail = imaplib.IMAP4_SSL(config.EMAIL_IMAP_HOST, config.EMAIL_IMAP_PORT)
        mail.login(config.EMAIL_IMAP_USER, config.EMAIL_IMAP_PASSWORD)
        mail.select("INBOX")

        status, data = mail.search(None, f"SINCE {since_date}")
        if status != "OK" or not data or not data[0]:
            mail.close()
            mail.logout()
            return []

        uids = data[0].split()

        for uid in uids:
            try:
                status, msg_data = mail.fetch(uid, "(RFC822.HEADER)")
                if status != "OK":
                    continue
                msg = _email.message_from_bytes(msg_data[0][1])

                all_addrs = []
                for header in ("From", "To", "Cc"):
                    raw = msg.get(header, "")
                    if raw:
                        all_addrs.extend(getaddresses([raw]))

                # Skip bulk/mailing-list messages
                if len(all_addrs) >= 10:
                    continue

                for name, addr in all_addrs:
                    addr = addr.lower().strip()
                    if not addr or "@" not in addr:
                        continue
                    if addr == config.EMAIL_IMAP_USER.lower():
                        continue
                    if addr not in addresses:
                        addresses[addr] = _decode_str(name) or None
            except Exception as e:
                print(f"[crm_email_scan] Message parse error: {e}")

        mail.close()
        mail.logout()

    except Exception as e:
        print(f"[crm_email_scan] IMAP error: {e}")
        _send(f"CRM email scan failed: {e}")

    return list(addresses.items())


def _decode_str(value: str) -> str:
    """Decode RFC 2047 encoded header value to a plain string."""
    if not value:
        return ""
    parts = _decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(str(part))
    return "".join(decoded).strip()


def _send_report(proposals: list, auto_added: list, skipped: int) -> None:
    """Send a Telegram summary of newly discovered contacts."""
    if not proposals and not auto_added:
        return

    lines = ["CRM Email Scan — Contacts Discovered\n"]

    if auto_added:
        lines.append(f"Auto-added ({len(auto_added)}):")
        for entry in auto_added:
            lines.append(f"  + {entry}")
        lines.append("")

    if proposals:
        # Show only first-time proposals or milestone seen counts
        notable = [p for p in proposals if p["seen_count"] == 1 or p["seen_count"] % 10 == 0]
        if notable:
            lines.append(f"New proposals ({len(notable)} shown of {len(proposals)}):")
            for p in notable[:15]:
                name_str = f"{p['name']} " if p.get("name") else ""
                lines.append(f"  ? {name_str}<{p['email']}> (seen {p['seen_count']}x)")
            lines.append("")
            lines.append("To add:  tell agent 'crm add <email>'")
            lines.append("To skip: tell agent 'crm skip <email>'")

    if skipped:
        lines.append(f"({skipped} addresses matched skip filters)")

    # Auto-add mode suggestion after enough decisions
    conn = crm._connect()
    decision_count = conn.execute("SELECT COUNT(*) FROM skip_patterns").fetchone()[0]
    conn.close()
    if 45 <= decision_count < 55:
        lines.append(
            f"\nTip: You've made {decision_count} skip decisions. "
            f"Consider enabling CRM_AUTO_ADD_MODE=true in .env for automatic contact adding."
        )

    _send("\n".join(lines))


def _send(text: str) -> None:
    """Send a Telegram message via raw requests (not python-telegram-bot)."""
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
            timeout=10,
        )
