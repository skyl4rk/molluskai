# TASK: Weather Report (On Demand)
# SCHEDULE: on demand
# ENABLED: false
# DESCRIPTION: Sends today's weather forecast to Telegram using wttr.in (no API key needed)

import requests
import config

# Set your location, or leave blank to auto-detect by IP address.
# Examples: "London", "New York", "48.8566,2.3522"
LOCATION = ""


def run():
    loc = LOCATION.strip()
    url = f"https://wttr.in/{loc}?format=3" if loc else "https://wttr.in/?format=3"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "curl/7.0"})
        resp.raise_for_status()
        _send(resp.text.strip())
    except Exception as e:
        _send(f"Weather unavailable: {e}")


def _send(text):
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
            timeout=10,
        )
