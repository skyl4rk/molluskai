# email_bot.py — IMAP polling + SMTP sending gateway
#
# Polls an email inbox for new messages, passes them through handle_message()
# (the same dispatcher used by Telegram and the terminal), and sends replies
# via SMTP. Supports an optional [FORWARD_EMAIL: address] directive in the
# LLM response to forward the email to a second recipient.
#
# All configuration is read from config.py (loaded from .env).
# If EMAIL_IMAP_HOST is not set, the gateway starts silently disabled.

import imaplib
import smtplib
import email as _email
import re
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from email.utils import parseaddr

import config


def start(message_handler) -> None:
    """
    Start the email gateway in a background daemon thread.
    message_handler: callable(text: str, reply_fn: callable) → None
                     This should be agent.handle_message.
    """
    if not config.EMAIL_IMAP_HOST:
        print("[email] EMAIL_IMAP_HOST not set — email gateway disabled.")
        return

    thread = threading.Thread(
        target=_run_email_loop,
        args=(message_handler,),
        daemon=True,
        name="email-bot",
    )
    thread.start()
    print(f"[email] Gateway started — polling {config.EMAIL_IMAP_USER} every {config.EMAIL_POLL_INTERVAL}s")


# ---------------------------------------------------------------------------
# Polling loop
# ---------------------------------------------------------------------------

def _run_email_loop(message_handler) -> None:
    """Poll IMAP inbox for unseen emails on a fixed interval."""
    while True:
        try:
            _poll_once(message_handler)
        except Exception as e:
            print(f"[email] Poll error: {e}")
        time.sleep(config.EMAIL_POLL_INTERVAL)


def _poll_once(message_handler) -> None:
    """Connect to IMAP, fetch unseen emails, process each one."""
    mail = imaplib.IMAP4_SSL(config.EMAIL_IMAP_HOST, config.EMAIL_IMAP_PORT)
    mail.login(config.EMAIL_IMAP_USER, config.EMAIL_IMAP_PASSWORD)
    mail.select("INBOX")

    status, data = mail.search(None, "UNSEEN")
    if status != "OK" or not data or not data[0]:
        mail.close()
        mail.logout()
        return

    for uid in data[0].split():
        try:
            status, msg_data = mail.fetch(uid, "(RFC822)")
            if status != "OK":
                continue
            raw = msg_data[0][1]
            msg = _email.message_from_bytes(raw)
            _handle_email(msg, message_handler)
        except Exception as e:
            print(f"[email] Error processing message {uid}: {e}")

    mail.close()
    mail.logout()


# ---------------------------------------------------------------------------
# Email processing
# ---------------------------------------------------------------------------

def _handle_email(msg, message_handler) -> None:
    """Parse one email, run it through the agent, and send the reply."""
    sender_name, sender_addr = parseaddr(msg.get("From", ""))
    subject  = _decode_header_str(msg.get("Subject", "(no subject)"))
    body     = _extract_text(msg).strip()

    if not sender_addr:
        return

    # Check sender whitelist (empty list = accept all)
    if config.EMAIL_ALLOWED_FROM and sender_addr not in config.EMAIL_ALLOWED_FROM:
        print(f"[email] Ignored (not in whitelist): {sender_addr}")
        return

    print(f"[email] Processing email from {sender_addr}: {subject}")

    # Build context string for the agent
    from_display = f"{sender_name} <{sender_addr}>" if sender_name else sender_addr
    context = (
        f"[Email received]\n"
        f"From: {from_display}\n"
        f"Subject: {subject}\n\n"
        f"{body}"
    )

    # Collect reply from the agent
    replies = []
    message_handler(context, lambda r: replies.append(r))
    full_reply = "\n\n".join(replies)

    if not full_reply:
        return

    # Extract [FORWARD_EMAIL:] directive if present
    cleaned_reply, forward = _extract_forward_directive(full_reply)

    # Send auto-reply to the original sender
    _send_email(
        to      = sender_addr,
        subject = f"Re: {subject}",
        body    = cleaned_reply,
    )
    print(f"[email] Auto-reply sent to {sender_addr}")

    # Forward if the agent requested it
    if forward:
        forward_body = (
            f"Forwarded email from {from_display}\n"
            f"Subject: {subject}\n"
            f"{'─' * 40}\n\n"
            f"{forward['body']}\n\n"
            f"{'─' * 40}\n"
            f"Original message:\n\n{body}"
        )
        _send_email(
            to      = forward["to"],
            subject = f"Fwd: {subject}",
            body    = forward_body,
        )
        print(f"[email] Forwarded to {forward['to']}")


# ---------------------------------------------------------------------------
# Directive extraction
# ---------------------------------------------------------------------------

def _extract_forward_directive(response: str) -> tuple:
    """
    Detect [FORWARD_EMAIL: address]...[/FORWARD_EMAIL] in an LLM response.
    If found, strips the tag and returns the cleaned response and forward details.
    Returns (cleaned_response, {"to": addr, "body": body} | None)
    """
    pattern = re.compile(
        r'\[FORWARD_EMAIL:\s*([^\]]+)\](.*?)\[/FORWARD_EMAIL\]',
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(response)
    if match:
        to_addr = match.group(1).strip()
        body    = match.group(2).strip()
        cleaned = pattern.sub("", response).strip()
        return cleaned, {"to": to_addr, "body": body}
    return response, None


# ---------------------------------------------------------------------------
# SMTP sending
# ---------------------------------------------------------------------------

def _send_email(to: str, subject: str, body: str) -> None:
    """Send a plain-text email via SMTP (STARTTLS on port 587)."""
    msg = MIMEMultipart()
    msg["From"]    = config.EMAIL_SMTP_USER
    msg["To"]      = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(config.EMAIL_SMTP_HOST, config.EMAIL_SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(config.EMAIL_SMTP_USER, config.EMAIL_SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"[email] SMTP error sending to {to}: {e}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_text(msg) -> str:
    """Return the plain-text body of an email, handling multipart messages."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                charset = part.get_content_charset() or "utf-8"
                try:
                    return part.get_payload(decode=True).decode(charset, errors="replace")
                except Exception:
                    return part.get_payload(decode=True).decode("utf-8", errors="replace")
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            return msg.get_payload(decode=True).decode(charset, errors="replace")
        except Exception:
            return msg.get_payload(decode=True).decode("utf-8", errors="replace")
    return ""


def _decode_header_str(value: str) -> str:
    """Decode an email header value that may be RFC 2047 encoded."""
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)
