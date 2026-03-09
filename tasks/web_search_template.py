# TASK: Web Search — <topic>
# SCHEDULE: every day at 08:00
# ENABLED: true
# DESCRIPTION: Searches the web for a topic each morning and reports the top 10 results with an AI summary

# --- Configure this task ---
SEARCH_TERM = "example search term"   # change this
TASK_LABEL  = "Example Topic"         # shown in the notification header
# --------------------------

import requests
import config
from notify import send
from websearch import search, format_results

TASK_MODEL = "google/gemini-2.0-flash-001"
MAX_RESULTS = 10


def run():
    results = search(SEARCH_TERM, max_results=MAX_RESULTS)
    if not results:
        send(f"Web search ({TASK_LABEL}): no results returned.")
        return

    formatted = format_results(results)
    summary = _summarise(SEARCH_TERM, formatted)

    msg = f"Morning search: {TASK_LABEL}\n\n"
    if summary:
        msg += f"{summary}\n\n---\n\n"
    msg += formatted
    send(msg)


def _summarise(topic: str, results_text: str) -> str:
    """Ask the LLM for a 2–3 sentence summary of today's search results."""
    prompt = (
        f"Here are today's top web search results for '{topic}':\n\n"
        f"{results_text}\n\n"
        "Write a concise 2–3 sentence summary of the key themes or news in these results. "
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
        print(f"[web_search] LLM error: {e}")
        return ""
