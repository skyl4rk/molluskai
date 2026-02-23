# orchestrator.py — Multi-agent orchestration
#
# Dispatches a user question to a panel of specialist subagents in parallel,
# each with a distinct role and (optionally) a different model. A synthesiser
# agent then reads all specialist outputs and produces one final response.
#
# Called from agent.py via the 'ensemble: <question>' command.
# No LLM credits are charged to the main agent's context — each call here
# goes directly to OpenRouter with its own model and system prompt.
#
# To customise:
#   - Edit SUBAGENTS to change specialist roles, models, or add/remove agents
#   - Edit SYNTHESISER to change the final synthesis model
#   - The number of subagents is flexible — threading adjusts automatically

import threading
import requests
import config

# ---------------------------------------------------------------------------
# Specialist subagents
# Each agent has a name, a model, and a role (its system prompt).
# ---------------------------------------------------------------------------

SUBAGENTS = [
    {
        "name":  "Analyst",
        "model": "google/gemini-2.0-flash-001",
        "role":  (
            "You are a rigorous analytical thinker. When given a question, "
            "break it down into its key components, identify underlying assumptions, "
            "and provide a structured, evidence-based analysis. Be precise and thorough. "
            "Keep your response to 150 words or fewer."
        ),
    },
    {
        "name":  "Devil's Advocate",
        "model": "meta-llama/llama-3.3-70b-instruct",
        "role":  (
            "You are a devil's advocate. When given a question, challenge its premise, "
            "surface counterarguments, identify risks and second-order consequences, "
            "and highlight what conventional thinking tends to overlook. "
            "Keep your response to 150 words or fewer."
        ),
    },
    {
        "name":  "Pragmatist",
        "model": "anthropic/claude-3-5-haiku",
        "role":  (
            "You are a pragmatist focused on real-world application. When given a question, "
            "focus on what is actually achievable, what constraints matter in practice, "
            "and what concrete next steps a person could take. Avoid theory. "
            "Keep your response to 150 words or fewer."
        ),
    },
]

# ---------------------------------------------------------------------------
# Synthesiser — reads all specialist outputs and produces the final answer
# ---------------------------------------------------------------------------

SYNTHESISER = {
    "model": "anthropic/claude-3-5-haiku",
    "role":  (
        "You are a synthesis expert. You receive responses from multiple specialists "
        "who have each analysed the same question from a different angle. "
        "Your job is to integrate their insights into one clear, balanced, and useful "
        "response. Do not list each specialist separately — weave their contributions "
        "into a single coherent answer. Keep the final response under 200 words."
    ),
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(question: str, reply_fn) -> None:
    """
    Orchestrate a multi-agent response to a user question.

    Steps:
      1. Acknowledge the request immediately
      2. Dispatch to all specialist subagents in parallel
      3. Pass all specialist outputs to the synthesiser
      4. Return the synthesised answer via reply_fn

    reply_fn: callable(str) — sends a message back to the user
    """
    specialist_names = ", ".join(a["name"] for a in SUBAGENTS)
    reply_fn(f"Consulting specialists: {specialist_names}…")

    # Step 1 — Run all subagents in parallel
    results = {}
    errors  = []

    def call_agent(agent: dict) -> None:
        response = _ask(agent["model"], agent["role"], question)
        if response:
            results[agent["name"]] = response
        else:
            errors.append(agent["name"])

    threads = [threading.Thread(target=call_agent, args=(agent,)) for agent in SUBAGENTS]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if not results:
        reply_fn("All specialist queries failed — check your API key and network connection.")
        return

    # Step 2 — Build the synthesis prompt
    answers_block = "\n\n".join(
        f"{name} ({_model_for(name)}):\n{text}"
        for name, text in results.items()
    )
    synthesis_prompt = (
        f"Question: {question}\n\n"
        f"Specialist analyses:\n\n{answers_block}\n\n"
        f"Synthesise these perspectives into one final response."
    )

    # Step 3 — Synthesise
    synthesis = _ask(SYNTHESISER["model"], SYNTHESISER["role"], synthesis_prompt)

    if synthesis:
        with open("synthesis_output.txt", "a") as f:
            f.write(f"Question: {question}\n\n{synthesis}\n\n---\n\n")
        reply_fn(synthesis)
    else:
        # Fallback: return the raw specialist outputs if synthesis fails
        reply_fn("Synthesis failed. Specialist responses:\n\n" + answers_block)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ask(model: str, system_prompt: str, user_message: str) -> str:
    """Call one model with a system prompt and user message. Returns reply text."""
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
                "messages": [
                    {"role": "system",  "content": system_prompt},
                    {"role": "user",    "content": user_message},
                ],
                "transforms": ["middle-out"],
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[orchestrator] Error from {model}: {e}")
        return ""


def _model_for(name: str) -> str:
    """Return the model ID for a named subagent (used in synthesis prompt)."""
    for agent in SUBAGENTS:
        if agent["name"] == name:
            return agent["model"]
    return "unknown"
