# TASK: Web Search — <topic>
# SCHEDULE: every day at 08:00
# ENABLED: true
# DESCRIPTION: Searches the web for a topic each morning and reports the top 10 results with an AI summary

# --- Configure this task ---
SEARCH_TERM = "example search term"   # change this
TASK_LABEL  = "Example Topic"         # shown in the notification header
# --------------------------

import requests
import smtplib, ssl
from email.mime.text import MIMEText
import config
from websearch import search, format_results

TASK_MODEL = "google/gemini-2.0-flash-001"
MAX_RESULTS = 10


def run():
    results = search(SEARCH_TERM, max_results=MAX_RESULTS)
    if not results:
        print(f"[web_search] No results for {TASK_LABEL}.")
        return

    formatted = format_results(results)
    summary = _summarise(SEARCH_TERM, formatted)

    body = f"Morning search: {TASK_LABEL}\n\n"
    if summary:
        body += f"{summary}\n\n---\n\n"
    body += formatted

    _send_email(f"Morning search: {TASK_LABEL}", body)


def _send_email(subject: str, body: str) -> None:
    to = config.EMAIL_FORWARD_ADDRESS
    if not to:
        print("[web_search] EMAIL_FORWARD_ADDRESS not set — skipping email.")
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
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
        print(f"[web_search] Email sent to {to}")
    except Exception as e:
        print(f"[web_search] Email error: {e}")


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
