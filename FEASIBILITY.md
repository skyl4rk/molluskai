# MolluskAI: Feasibility Review & Recommendations

## Reference Project: PicoClaw

PicoClaw (https://github.com/sipeed/picoclaw, written in Go) provides useful design patterns to adopt:
- Markdown files for memory: `MEMORY.md`, `IDENTITY.md`, `sessions/`
- Skills stored as files in a `skills/` directory
- A heartbeat file checked every 30 minutes for scheduled tasks
- Multiple LLM providers via abstraction layer (including OpenRouter)
- Multiple gateways: Telegram, Discord, LINE, etc.
- Startup time under 1 second, RAM under 10MB

MolluskAI follows similar patterns but in Python, which is more appropriate for the Raspberry Pi learning platform goal.

---

## Component Feasibility

### OpenRouter.ai Integration — HIGH feasibility
OpenRouter provides an OpenAI-compatible REST API. A minimal Python implementation needs only `requests` or `httpx`. The `/models` endpoint can be queried to populate a dropdown of available models.

Recommended popular models for the onboarding dropdown:
- google/gemini-2.0-flash-001
- anthropic/claude-3-5-haiku
- openai/gpt-4o-mini
- meta-llama/llama-3.3-70b-instruct
- mistralai/mistral-7b-instruct
- deepseek/deepseek-chat

### Raspberry Pi 4/5 ARM64 — HIGH feasibility
Python, `python-telegram-bot`, `requests`, `sqlite-vec`, and `tkinter` all run well on ARM64 Raspberry Pi OS. The 4GB+ RAM models handle all proposed components comfortably.

### Terminal Agent Interface — HIGH feasibility
A Python readline-based loop is 20–30 lines of code. This should be the first deliverable and the primary development and testing surface.

### Telegram Gateway — HIGH feasibility
`python-telegram-bot` in polling mode is the right choice. Polling avoids needing to expose the Pi to the internet. No port forwarding required. Bot token is sufficient.

### Python GUI Onboarding — HIGH feasibility
`tkinter` (Python stdlib, included in Raspberry Pi OS full desktop) is the right tool. `ttk.Combobox` provides the model dropdown. Text entry fields handle the API key and Telegram token. On first launch, if no config exists, show the GUI; thereafter, load from `.env`.

**Limitation**: Requires full Raspberry Pi OS desktop, not Lite. Headless or SSH installs should fall back to terminal-based setup prompts.

### Local Cron / Python Task Execution — HIGH feasibility
Smart cost-reduction design. Use Python's `schedule` library (runs within the agent process) or system `cron` (runs independently). See the Skills and Tasks section below.

---

## Database: sqlite-vec — RECOMMENDED with caveat

**Recommendation: Use sqlite-vec.**

sqlite-vec is the right fit for this project:
- No separate server process (unlike ChromaDB)
- Pure SQLite file on disk — trivial to back up and portable
- NEON SIMD acceleration on ARM64 — fast KNN search
- Very low memory footprint — important for Raspberry Pi

**ARM64 caveat**: Pre-built ARM64 wheels may not be available on PyPI. Installation may require building from source (`pip install sqlite-vec` will attempt this if no wheel is found, but requires `gcc` and `make`). This should be validated early and documented in the setup instructions.

**Fallback**: If sqlite-vec build fails, a pure-Python fallback using numpy cosine similarity over embeddings stored as SQLite BLOBs is trivial to implement for the small dataset sizes expected on a personal device.

**Embeddings**: OpenRouter does not provide an embeddings API. Recommended approach: use `fastembed` with the `BAAI/bge-small-en-v1.5` model (~24MB). It runs locally on ARM64, requires no external API key, and produces 384-dimension vectors suitable for semantic search. Embeddings remain entirely local and free.

---

## Skills and Tasks: Two Distinct Types

The project should define two separate automation concepts with distinct names and implementations.

### Skills (AI Prompt Templates)
- **What they are**: Markdown files containing prompt instructions sent to the LLM.
- **Stored in**: `skills/` directory as `.md` files.
- **How they work**: The agent loads a skill file and injects its contents into the conversation. The LLM acts on the instructions.
- **Examples**:
  - "If I send you a PDF, extract the text using Python and store it in the database."
  - "When I ask for an AI cost report, summarise my usage logs in 3 bullet points and send it to Telegram."
- **User-editable**: Yes — plain text files. The user can edit them directly or ask the LLM to rewrite them.
- **LLM-writeable**: Yes — the agent can create or update skill files on request.

### Tasks (Local Python/Cron Automation)
- **What they are**: Python scripts that run locally on a schedule, without calling the LLM.
- **Stored in**: `tasks/` directory as `.py` files, each with a metadata header (schedule, description).
- **How they work**: A scheduler (`schedule` library or system cron) runs the script at the defined interval.
- **Examples**:
  - Send a daily usage summary to Telegram at 8am.
  - Fetch and store weather data every hour.
  - Rotate log files weekly.
- **LLM cost**: Zero. Tasks run locally with no API calls.
- **User-editable**: Yes — plain Python. Readable and modifiable by anyone learning to code.

This two-type system maps directly to picoclaw's approach of separating scheduled local actions from LLM-driven skill interactions.

---

## Context & Memory Management — RECOMMENDATION

This is the most important architectural decision for cost control. The recommendation is a three-layer context model.

### Layer 1: System Prompt (fixed, ~300–500 tokens)
- Agent identity and behaviour instructions.
- Loaded from `IDENTITY.md`, following the picoclaw convention.
- Rarely changes between sessions.

### Layer 2: Retrieved Memories (dynamic, ~400–600 tokens)
- On each user message, embed the message and run a KNN search in sqlite-vec.
- Inject the top 3–5 most semantically relevant past memories as a brief block.
- This is the RAG (retrieval-augmented generation) layer.
- Only what is relevant to the current query is injected — not the entire memory store.

### Layer 3: Recent Conversation (sliding window, ~1500–2000 tokens)
- Keep the last 10–15 turns of the current session.
- Store all turns in SQLite for persistence across sessions.

### OpenRouter Middle-Out
Enable `transforms: ["middle-out"]` on all requests. This is a safety net: if the assembled context exceeds the model's context window (unlikely with the limits above, but possible), OpenRouter will trim the middle of the conversation rather than returning an error. It is not a substitute for local context management — it is a graceful overflow handler.

**Practical result**: Most requests will consume 2500–3500 tokens of input context, keeping costs predictable and low while providing relevant memory recall.

### Memory Storage Flow
1. User sends a message.
2. Embed the message → query sqlite-vec for the top 5 relevant past memories.
3. Build the prompt: system prompt + retrieved memories + recent conversation + user message.
4. Send to OpenRouter with middle-out enabled.
5. Store the user message and LLM response as a new memory entry with embedding.

### User-Initiated Memory Search
The user types `search: <topic>` (or a similar command prefix).
The agent embeds the query and returns the top N matching memory entries displayed in chat.

### Document and URL Ingestion
- **URL**: User sends a link → `requests` fetches the page → `BeautifulSoup` strips HTML → chunk into ~500-token segments → embed each chunk → store in sqlite-vec with source URL metadata.
- **PDF**: User sends a file path or Telegram attachment → `pymupdf` or `pdfminer` extracts text → chunk → embed → store.
- All stored documents are retrievable via semantic search or by filtering on source URL metadata.

---

## Security Model: .env File — ADEQUATE

A `.env` file loaded with `python-dotenv` is the recommended approach. This is adequate for a personal Raspberry Pi device that:
- Is not publicly accessible (Telegram polling requires no open ports)
- Is used by a single user
- Is on a home or private network

Recommended practices:
- Set file permissions: `chmod 600 .env`
- Add `.env` to `.gitignore` to prevent accidental commits
- Document clearly that users should not share the file

The `.env` file stores: `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `TELEGRAM_TOKEN`.

A more hardened option such as the Linux `keyring` adds complexity without meaningful benefit for this use case. The `.env` approach is also more readable and teachable, which fits the Raspberry Pi learning platform goal.

---

## Calendar & Email — RECOMMENDATION

### Email — Yes, as an optional Task or Skill
- Python's stdlib `imaplib` and `smtplib` handle IMAP read and SMTP send.
- No third-party dependencies required.
- A basic email-checking task is approximately 50 lines of Python.
- Works with any provider supporting IMAP (Gmail, Outlook, self-hosted).
- Natural fit as a Task (scheduled inbox check) or a Skill (ask the agent to draft and send an email).

### Calendar — Defer
- CalDAV integration varies significantly by provider (Google, Nextcloud, Apple iCloud) and adds setup friction.
- No Raspberry Pi desktop app exposes a clean Python API.
- Most calendar use cases can be approximated with a local plain-text schedule file queried by the agent.
- Recommended: mark calendar support as a future planned skill, not a v1 requirement.

---

## Recommended Project Structure

```
molluskai/
├── agent.py           # Core agent loop (terminal + message dispatch)
├── config.py          # Load .env, validate config
├── llm.py             # OpenRouter API calls
├── memory.py          # sqlite-vec store, retrieve, search
├── telegram_bot.py    # Telegram polling gateway
├── onboarding.py      # tkinter GUI for first-run setup
├── scheduler.py       # Task scheduler (schedule library)
├── skills/            # .md files — AI prompt templates
│   └── example.md
├── tasks/             # .py files — local automation scripts
│   └── example.py
├── data/
│   └── memory.db      # sqlite-vec database
├── IDENTITY.md        # Agent persona and system prompt
├── .env               # API keys (never committed)
└── requirements.txt
```

---

## Phased Roadmap

- **Phase 1 (Core)**: Terminal interface + OpenRouter + `.env` config + onboarding GUI
- **Phase 2 (Gateway)**: Telegram polling
- **Phase 3 (Memory)**: sqlite-vec + fastembed + document and URL ingestion
- **Phase 4 (Automation)**: Skills and Tasks system + scheduler
- **Phase 5 (Productivity)**: Email (IMAP/SMTP) as an example Task
- **Phase 6 (Stretch)**: Community-contributed skills and tasks

---

## Strengths of the Concept

- **Cost-conscious by design**: local Tasks, semantic retrieval, and a sliding context window all reduce token spend.
- **OpenRouter integration**: single API key, access to dozens of models, easy to switch.
- **Skills-as-markdown and Tasks-as-Python**: readable, editable, and appropriate for a learning platform audience.
- **Two-gateway design**: terminal for development, Telegram for everyday use.
- **Simple onboarding**: three fields and a dropdown — minimal barrier to first run.
- **Project structure mirrors picoclaw**: proven patterns adapted to Python.
- **Extensible by design**: new skills and tasks are file additions, not code changes.
