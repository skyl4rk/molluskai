# TASK: Everglades Challenge Monitor
# SCHEDULE: every day at 05:48
# ENABLED: false
# DESCRIPTION: Daily digest of Everglades Challenge/WaterTribe updates

import requests
import smtplib, ssl
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText
import config
from datetime import datetime, timedelta

KEYWORD = "Everglades Challenge"
FEEDS = [
    "https://www.watertribe.com/feed/",  # WaterTribe blog RSS
    "https://hnrss.org/frontpage",
]

def run():
    cutoff = datetime.utcnow() - timedelta(hours=25)
    matches = []

    for feed_url in FEEDS:
        try:
            resp = requests.get(feed_url, timeout=10, headers={"User-Agent": "MolluskAI/1.0"})
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item"):
                title = item.findtext("title") or ""
                link  = item.findtext("link")  or ""
                desc  = item.findtext("description") or ""
                if KEYWORD.lower() in (title + " " + desc).lower():
                    matches.append(f"• {title.strip()}\n  {link.strip()}")
        except Exception as e:
            print(f"[everglades_monitor] Error fetching {feed_url}: {e}")

    if not matches:
        return

    header  = f"Everglades Challenge Monitor\n{datetime.now().strftime('%Y-%m-%d')}\n"
    message = header + "\n\n".join(matches[:10])
    _send(message)


def _send(text):
    to = config.EMAIL_FORWARD_ADDRESS
    if not to:
        print("[everglades_monitor] EMAIL_FORWARD_ADDRESS not set — skipping email.")
        return
    msg = MIMEText(text)
    msg["Subject"] = "Everglades Challenge Monitor"
    msg["From"]    = config.EMAIL_SMTP_USER
    msg["To"]      = to
    try:
        if config.EMAIL_SMTP_PORT == 465:
            with smtplib.SMTP_SSL(config.EMAIL_SMTP_HOST, config.EMAIL_SMTP_PORT, context=ssl.create_default_context()) as s:
                s.login(config.EMAIL_SMTP_USER, config.EMAIL_SMTP_PASSWORD)
                s.send_message(msg)
        else:
            with smtplib.SMTP(config.EMAIL_SMTP_HOST, config.EMAIL_SMTP_PORT) as s:
                s.ehlo()
                s.starttls()
                s.login(config.EMAIL_SMTP_USER, config.EMAIL_SMTP_PASSWORD)
                s.send_message(msg)
        print(f"[everglades_monitor] Email sent to {to}")
    except Exception as e:
        print(f"[everglades_monitor] Email error: {e}")