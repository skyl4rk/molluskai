# TASK: Ensemble Daily Insight
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: Three models answer the same question in parallel, a fourth synthesises their answers into one refined response, sent to Telegram

import threading
import requests
import config

# The question sent to all three panel models each morning
DAILY_QUESTION = "What is one practical thing a person can do today to think more clearly and make better decisions?"

# Panel: three fast, diverse models answer independently
PANEL_MODELS = [
    ("Haiku",  "anthropic/claude-3-5-haiku"),
    ("Gemini", "google/gemini-2.0-flash-001"),
    ("Llama",  "meta-llama/llama-3.3-70b-instruct"),
]

# Synthesiser: reviews all three answers and produces one refined response
SYNTHESISER_MODEL = "anthropic/claude-3-5-haiku"


def run():
    # Step 1 — Ask all panel models in parallel
    panel_results = {}

    def ask_panel(name, model):
        panel_results[name] = _ask(model, DAILY_QUESTION)

    threads = [threading.Thread(target=ask_panel, args=(name, model))
               for name, model in PANEL_MODELS]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Step 2 — Build the synthesis prompt from all three answers
    answers_block = "\n\n".join(
        f"{name}:\n{panel_results.get(name, '(no response)')}"
        for name, _ in PANEL_MODELS
    )
    synthesis_prompt = (
        f"Three AI models were asked: \"{DAILY_QUESTION}\"\n\n"
        f"Their answers:\n\n{answers_block}\n\n"
        f"Synthesise the best ideas from all three answers into one clear, "
        f"practical response of no more than 80 words. Do not mention the models "
        f"or that this is a synthesis — just give the refined answer directly."
    )

    # Step 3 — Synthesise
    synthesis = _ask(SYNTHESISER_MODEL, synthesis_prompt)

    if synthesis:
        message = f"Daily insight:\n\n{synthesis}"
        _send(message)


def _ask(model: str, prompt: str) -> str:
    """Send a prompt to a specific OpenRouter model and return the reply."""
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://github.com/skyl4rk/molluskai",
                "X-Title": "MolluskAI",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[ensemble] Error from {model}: {e}")
        return ""


def _send(text: str) -> None:
    """Send a Telegram message."""
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
            timeout=10,
        )
