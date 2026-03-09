# TASK: Daily Quote
# SCHEDULE: every day at 05:18
# ENABLED: false
# DESCRIPTION: Generates a daily stoic quote and reflection using a specified model, sends to Telegram

import requests
import config
from notify import send

# Use a different model from the main agent — cheap and fast for short tasks
TASK_MODEL = "anthropic/claude-3-5-haiku"


def run():
    reply = _ask("Give me a single stoic quote and a one-sentence reflection on how it applies to daily life. Keep it under 60 words total.")
    if reply:
        send(f"Daily thought:\n\n{reply}")


def _ask(prompt: str) -> str:
    """Send a prompt to OpenRouter and return the reply text."""
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
        print(f"[daily_quote] LLM error: {e}")
        return ""


