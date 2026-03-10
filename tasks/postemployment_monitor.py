# TASK: Postemployment Monitor
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: Daily updates on postemployment, unemployment, job market topics

import requests
import xml.etree.ElementTree as ET
import config
from datetime import datetime, timedelta

KEYWORD = "postemployment"
FEEDS = [
    "https://hnrss.org/frontpage",  # Hacker News
    "https://www.reddit.com/r/economics/new.json",  # Economics discussions
    "https://www.reddit.com/r/jobs/new.json",       # Jobs/career discussions
]

def run():
    cutoff = datetime.utcnow() - timedelta(hours=25)
    matches = []

    # Hacker News RSS
    try:
        resp = requests.get(FEEDS[0], timeout=10, headers={"User-Agent": "MolluskAI/1.0"})
        root = ET.fromstring(resp.content)
        for item in root.findall(".//item"):
            title = item.findtext("title") or ""
            link  = item.findtext("link")  or ""
            desc  = item.findtext("description") or ""
            if KEYWORD.lower() in (title + " " + desc).lower():
                matches.append(f"• {title.strip()}\n  {link.strip()}")
    except Exception as e:
        print(f"[postemployment_monitor] Error fetching HN RSS: {e}")

    # Reddit feeds
    for subreddit in ["economics", "jobs"]:
        try:
            resp = requests.get(
                f"https://www.reddit.com/r/{subreddit}/new.json",
                params={"limit": 50},
                headers={"User-Agent": "MolluskAI/1.0"},
                timeout=10,
            )
            posts = resp.json()["data"]["children"]
            for post in posts:
                d = post["data"]
                if d.get("created_utc", 0) < cutoff.timestamp():
                    continue
                title = d.get("title", "")
                body  = d.get("selftext", "")
                if KEYWORD.lower() in (title + " " + body).lower():
                    url = f"https://reddit.com{d.get('permalink', '')}"
                    matches.append(f"• {title.strip()} (r/{subreddit})\n  {url}")
        except Exception as e:
            print(f"[postemployment_monitor] Error fetching Reddit {subreddit}: {e}")

    if not matches:
        return

    header = f"Postemployment Monitor\n{datetime.now().strftime('%Y-%m-%d')}\n"
    message = header + "\n\n".join(matches[:10])
    _send(message)


def _send(text):
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
            timeout=10,
        )