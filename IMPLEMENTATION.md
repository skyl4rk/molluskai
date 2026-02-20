# MolluskAI: Implementation Plan

## Project Structure

```
molluskai/
├── agent.py           # Entry point and core agent loop
├── config.py          # .env loading and validation
├── llm.py             # OpenRouter API calls
├── memory.py          # sqlite-vec + fastembed, numpy fallback
├── onboarding.py      # tkinter GUI (terminal fallback if headless)
├── telegram_bot.py    # Telegram polling in background thread
├── scheduler.py       # Task discovery and scheduling
├── IDENTITY.md        # Agent system prompt / persona
├── .env.example       # Template for users to copy
├── .gitignore
├── requirements.txt
├── skills/
│   ├── how_to_write_a_skill.md
│   ├── pdf_ingestion.md
│   └── cost_report.md
└── tasks/
    ├── README.md
    └── daily_report.py   (disabled by default)
```

---

## Dependencies (requirements.txt)

```
requests
python-dotenv
python-telegram-bot>=20.0
schedule
fastembed
sqlite-vec
beautifulsoup4
pymupdf
```

`tkinter` is Python stdlib and requires no installation. `fastembed` and `sqlite-vec` are optional at runtime — the agent degrades gracefully if either is missing.

---

## File-by-File Design

### config.py
- Load `.env` with `python-dotenv`
- Expose `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `TELEGRAM_TOKEN` as module constants
- `is_configured() -> bool`: returns True if `.env` exists and required keys are present
- `POPULAR_MODELS`: hardcoded list used by the onboarding dropdown

---

### llm.py
- `chat(messages, system_prompt) -> str`: POST to `https://openrouter.ai/api/v1/chat/completions`
- Request body includes `transforms: ["middle-out"]` to handle context overflow gracefully
- Appends token usage and estimated cost to `data/usage.log` after each call
- `get_models() -> list[str]`: fetches `/api/v1/models` and returns model ID strings (used by onboarding)

---

### memory.py

**Embeddings** (with graceful fallback):
- Try to import `fastembed`. If available, use `TextEmbedding("BAAI/bge-small-en-v1.5")` (~24MB, runs locally on ARM64)
- If fastembed is unavailable, `embed()` returns `None` and memory falls back to SQLite FTS5 full-text search

**Database setup**:
- Try to import `sqlite_vec`. If available, create a `vec0` virtual table for KNN search alongside a regular `memories` table.
- If sqlite-vec is unavailable, use numpy cosine similarity over embeddings stored as SQLite BLOBs.
- Tables:
  - `memories(id, content, role, source, timestamp)` — the text store
  - `memories_vec` — virtual vec0 table with 384-dim float embeddings
  - `conversation(id, role, content, timestamp)` — session history

**Public API**:
- `store_memory(content, role="note", source=None)`: embed + insert into both tables
- `store_conversation(role, content)`: insert into conversation table
- `search(query, n=5) -> list[dict]`: KNN via sqlite-vec (or numpy fallback), returns top N memories
- `get_recent(n=15) -> list[dict]`: last N rows from conversation table as `{role, content}` dicts
- `ingest_url(url) -> str`: fetch → BeautifulSoup strip HTML → chunk (~400 words) → embed each chunk → store. Returns summary.
- `ingest_pdf(path) -> str`: pymupdf extract text → chunk → embed → store. Returns summary.

---

### agent.py

**Startup sequence**:
1. If `not is_configured()`: run `onboarding.run()`
2. Load config and init memory (creates DB if needed)
3. Start scheduler in a daemon thread
4. Start Telegram bot in a daemon thread (if `TELEGRAM_TOKEN` is set)
5. Run terminal loop in the main thread

**`handle_message(text, reply_fn) -> None`**:
Single dispatch function used by both terminal and Telegram to avoid code duplication.

| Input | Action | LLM call? |
|-------|--------|-----------|
| `help` or `?` | Print command list | No |
| `skills` | List `.md` files in `skills/` | No |
| `tasks` | List tasks with schedule metadata | No |
| `search: <query>` | Semantic memory search | No |
| `ingest: <url>` or bare URL | Fetch and store URL | No |
| Anything else | Build context → LLM → store | Yes |

**`build_context(user_message) -> (system_str, messages_list)`**:
- Layer 1 (~400 tokens): Read `IDENTITY.md` + concatenate all `skills/*.md` → system string
- Layer 2 (~500 tokens): `memory.search(user_message, n=5)` → format as "Relevant memories:" block, prepend as a system message
- Layer 3 (~2000 tokens): `memory.get_recent(n=15)` → list of `{role, content}` dicts

**Terminal loop**:
```python
while True:
    text = input("you> ").strip()
    if text in ("exit", "quit"):
        break
    handle_message(text, reply_fn=lambda r: print(f"agent> {r}"))
```

---

### telegram_bot.py
- `start(token, message_handler)`: runs `python-telegram-bot` in its own asyncio event loop in a daemon thread
- Handles TEXT messages and DOCUMENT messages (PDF auto-ingestion via Telegram file download)
- Calls `message_handler(text, reply_fn)` which is `agent.handle_message`
- Splits replies longer than 4096 characters (Telegram message limit)

---

### onboarding.py

**`run()`**:
- Try to import tkinter. If available, show the GUI window.
- If tkinter is unavailable (headless Pi), fall back to `input()` prompts.

**tkinter GUI**:
- Title: "MolluskAI Setup"
- Fields: API Key (Entry, masked), Model (ttk.Combobox), Telegram Token (Entry)
- "Fetch models from OpenRouter" button → calls `llm.get_models()`, populates combobox
- "Save & Start" button → writes `.env` file, closes window
- Window sized 480×320, centred on screen

**Terminal fallback**:
- `input()` prompts for each value
- Model selection via numbered list
- Writes the same `.env` file

**`write_env(api_key, model, telegram_token)`**: writes `.env` and sets `chmod 600`.

---

### scheduler.py
- `discover_tasks() -> list[dict]`: scan `tasks/*.py`, parse header comment block for TASK / SCHEDULE / ENABLED / DESCRIPTION
- `start()`: for each enabled task, register with the `schedule` library, then run `schedule.run_pending()` in a loop in a daemon thread

**Task metadata header format**:
```python
# TASK: Name
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: What this task does
```

---

## Skills

### skills/how_to_write_a_skill.md
Documents the skill format for the user and the LLM. Tells the LLM it can create or edit skill files on request.

### skills/pdf_ingestion.md
Instructs the LLM: when the user provides a file path ending in `.pdf`, call the ingest command on it.

### skills/cost_report.md
Instructs the LLM: when asked for a usage or cost report, read `data/usage.log` and summarise token counts and estimated costs concisely.

---

## Tasks

### tasks/daily_report.py
Disabled by default. Reads `data/usage.log` and sends a brief daily usage summary to Telegram at 08:00. Enable by setting `# ENABLED: true` and adding a `TELEGRAM_CHAT_ID` to `.env`.

---

## Key Design Principles

- Every optional import (`fastembed`, `sqlite_vec`, `telegram`, `tkinter`) is wrapped in `try/except` so the core agent runs even if a dependency fails to install.
- `agent.handle_message()` is the single dispatch point — no duplication between terminal and Telegram paths.
- Code is written to be readable: short functions, clear names, comments on non-obvious logic. This is a learning platform project.
- No classes where a module-level function will do.
- Target: approximately 900 lines of Python across all files.

---

## ARM64 Installation Note

`sqlite-vec` may not have pre-built ARM64 wheels on PyPI. If `pip install sqlite-vec` fails, build from source:
```bash
sudo apt install gcc make
pip install sqlite-vec
```
If this fails, the agent falls back automatically to numpy-based cosine similarity. Document this clearly in the README.

---

## Verification Checklist

1. `python agent.py` with no `.env` → onboarding GUI appears (or terminal prompts if headless)
2. After onboarding, `.env` is written with correct values
3. `python agent.py` with valid `.env` → agent starts, shows prompt
4. Type a message → LLM responds
5. `search: raspberry pi` → returns memory results (or "no memories yet")
6. `ingest: https://example.com` → page fetched and stored, confirmation shown
7. `skills` command → lists skill files with names
8. `tasks` command → lists task files with schedule info
9. Telegram message → agent responds (requires `TELEGRAM_TOKEN` in `.env`)
10. Remove sqlite-vec → fallback mode activates, agent still starts and responds
