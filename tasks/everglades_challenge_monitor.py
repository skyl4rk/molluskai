# TASK: Everglades Challenge Monitor
# SCHEDULE: every day at 05:48
# ENABLED: false
# DESCRIPTION: Daily digest of Everglades Challenge/WaterTribe updates

import requests
import xml.etree.ElementTree as ET
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
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
            timeout=10,
        )