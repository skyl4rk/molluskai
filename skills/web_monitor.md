# Web Monitor — Daily Keyword Reports

## Purpose

Create scheduled tasks that monitor web sources for a keyword and send a daily digest to Telegram. No API keys required for any of the sources below.

## When the user asks for a web monitor

Ask (or infer from context):
1. **What keyword or topic** to monitor
2. **Which source** — news/RSS, Hacker News, Reddit, or a specific URL
3. **What time** to deliver the report (default: every day at 08:00)

Then generate a complete task using the appropriate template below and wrap it in `[SAVE_TASK: filename.py]`.

---

## Template 1 — RSS / News feeds

Use for: general news, blogs, podcasts. Edit the `FEEDS` list to match the topic.

```python
# TASK: RSS Monitor — {keyword}
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: Daily digest of RSS feed items matching '{keyword}'

import requests
import xml.etree.ElementTree as ET
import config
from datetime import datetime, timedelta

KEYWORD = "{keyword}"
FEEDS = [
    # Add RSS feed URLs here. Examples:
    # "https://feeds.bbci.co.uk/news/technology/rss.xml",
    # "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    # "https://hnrss.org/frontpage",
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
            print(f"[rss_monitor] Error fetching {feed_url}: {e}")

    if not matches:
        return

    header  = f"RSS Monitor: '{KEYWORD}'\n{datetime.now().strftime('%Y-%m-%d')}\n"
    message = header + "\n\n".join(matches[:10])
    _send(message)


def _send(text):
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
            timeout=10,
        )
```

---

## Template 2 — Hacker News

Use for: tech topics, programming, startups, science. Free Algolia API, no key needed.

```python
# TASK: HN Monitor — {keyword}
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: Daily Hacker News stories matching '{keyword}'

import requests
import config
from datetime import datetime, timedelta

KEYWORD = "{keyword}"

def run():
    cutoff = int((datetime.utcnow() - timedelta(hours=25)).timestamp())
    try:
        resp = requests.get(
            "https://hn.algolia.com/api/v1/search_by_date",
            params={
                "query": KEYWORD,
                "tags": "story",
                "numericFilters": f"created_at_i>{cutoff}",
                "hitsPerPage": 10,
            },
            timeout=10,
        )
        hits = resp.json().get("hits", [])
    except Exception as e:
        print(f"[hn_monitor] Error: {e}")
        return

    if not hits:
        return

    lines = [f"Hacker News: '{KEYWORD}'\n{datetime.now().strftime('%Y-%m-%d')}"]
    for h in hits:
        title  = h.get("title", "")
        url    = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        points = h.get("points", 0)
        lines.append(f"• {title} ({points} pts)\n  {url}")

    _send("\n\n".join(lines))


def _send(text):
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
            timeout=10,
        )
```

---

## Template 3 — Reddit

Use for: community discussions on a specific subreddit. No API key needed for public subreddits.

```python
# TASK: Reddit Monitor — r/{subreddit} — {keyword}
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: Daily new posts in r/{subreddit} matching '{keyword}'

import requests
import config
from datetime import datetime, timedelta

SUBREDDIT = "{subreddit}"   # e.g. raspberry_pi, homeautomation, selfhosted
KEYWORD   = "{keyword}"     # leave empty to get all new posts

def run():
    cutoff = (datetime.utcnow() - timedelta(hours=25)).timestamp()
    try:
        resp = requests.get(
            f"https://www.reddit.com/r/{SUBREDDIT}/new.json",
            params={"limit": 50},
            headers={"User-Agent": "MolluskAI/1.0"},
            timeout=10,
        )
        posts = resp.json()["data"]["children"]
    except Exception as e:
        print(f"[reddit_monitor] Error: {e}")
        return

    matches = []
    for post in posts:
        d = post["data"]
        if d.get("created_utc", 0) < cutoff:
            continue
        title = d.get("title", "")
        body  = d.get("selftext", "")
        if not KEYWORD or KEYWORD.lower() in (title + " " + body).lower():
            url = f"https://reddit.com{d.get('permalink', '')}"
            matches.append(f"• {title.strip()}\n  {url}")

    if not matches:
        return

    header  = f"Reddit r/{SUBREDDIT}: '{KEYWORD}'\n{datetime.now().strftime('%Y-%m-%d')}\n"
    message = header + "\n\n".join(matches[:10])
    _send(message)


def _send(text):
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
            timeout=10,
        )
```

---

## Template 4 — Specific URL keyword watch

Use for: a page that doesn't have an RSS feed — job boards, local council notices, small websites. Sends an alert whenever the keyword appears on the page. Note: fires every day the keyword is present, not just the first time.

```python
# TASK: Page Watch — {keyword} at {url}
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: Alert when '{keyword}' appears on {url}

import requests
import config
from datetime import datetime

URL     = "{url}"
KEYWORD = "{keyword}"

def run():
    try:
        from bs4 import BeautifulSoup
        resp = requests.get(URL, timeout=15, headers={"User-Agent": "MolluskAI/1.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(separator=" ")
    except Exception as e:
        print(f"[page_watch] Error: {e}")
        return

    if KEYWORD.lower() in text.lower():
        _send(
            f"Page Watch: '{KEYWORD}' found\n"
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"{URL}"
        )


def _send(text):
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
            timeout=10,
        )
```

---

## Choosing a source

| Source | Best for | Notes |
|--------|----------|-------|
| RSS feeds | News sites, blogs, podcasts | Most reliable; many sites publish RSS |
| Hacker News | Tech, programming, science | Free Algolia API; 25-hour lookback |
| Reddit | Community topics, hobbies | Public subreddits only; no key needed |
| Page watch | Any specific URL | Alerts whenever keyword is present |

## After generating the task

Remind the user to:
1. Review the generated code before enabling
2. Enable it: `enable task: <filename>`
3. The first report arrives at the scheduled time
