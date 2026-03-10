# TASK: MolluskAI Mentions Monitor
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: Daily DuckDuckGo search for 'molluskai' — LLM summary emailed to EMAIL_FORWARD_ADDRESS

import sys
from pathlib import Path
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

import requests
import config
import web_search
import email_bot

SEARCH_TERM = "molluskai"
TASK_LABEL  = "MolluskAI Mentions"
TASK_MODEL  = "google/gemini-2.0-flash-001"
MAX_RESULTS = 10


def run():
    results = web_search.search(SEARCH_TERM, max_results=MAX_RESULTS)
    summary = _summarise(SEARCH_TERM, results)

    body = f"Morning search: {TASK_LABEL}\n\n"
    if summary:
        body += f"{summary}\n\n---\n\n"
    body += results

    email_bot.send_email(
        to      = config.EMAIL_FORWARD_ADDRESS,
        subject = f"Morning search: {TASK_LABEL}",
        body    = body,
    )
    print(f"[molluskai_monitor] Email sent to {config.EMAIL_FORWARD_ADDRESS}")


def _summarise(topic: str, results_text: str) -> str:
    prompt = (
        f"Here are today's top web search results for '{topic}':\n\n"
        f"{results_text}\n\n"
        "Write a concise 2-3 sentence summary of the key themes or findings. "
        "Be factual and direct."
    )
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://github.com/skyl4rk/molluskai",
                "X-Title": "MolluskAI",
            },
            json={
                "model": TASK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[molluskai_monitor] LLM error: {e}")
        return ""


if __name__ == "__main__":
    run()
