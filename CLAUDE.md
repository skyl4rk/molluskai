# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Agent

```bash
cd ~/molluskai
source venv/bin/activate

python agent.py                  # terminal + Telegram + scheduler (normal use)
python agent.py --no-terminal    # headless: Telegram + scheduler only (systemd)
python agent.py --terminal       # attach an SSH terminal to a running headless instance
```

Install dependencies:
```bash
pip install -r requirements.txt
sudo apt install ffmpeg           # for voice transcription (faster-whisper)
sudo apt install gcc make libsqlite3-dev  # if sqlite-vec needs to be built from source
```

## Architecture

MolluskAI is a Raspberry Pi AI agent that uses OpenRouter for LLM access and stores all memory locally in SQLite.

**Startup sequence (`agent.py`):**
1. `config.py` — loads `.env` into module-level constants; calls `onboarding.py` if unconfigured
2. `memory.init()` — creates SQLite tables in `data/memory.db`
3. `scheduler.start()` — discovers `tasks/*.py`, registers enabled ones with the `schedule` library in a daemon thread
4. `telegram_bot.start(handle_message)` — polls Telegram in a daemon thread
5. `email_bot.start(handle_message)` — polls IMAP in a daemon thread (if `EMAIL_IMAP_HOST` is set)
6. Unix socket server starts at `/tmp/molluskai.sock` — allows `--terminal` SSH sessions to connect to the running headless instance
7. Terminal loop (or headless wait)

**Central dispatcher:** All input from terminal, Telegram, and email goes through `handle_message(text, reply_fn)` in `agent.py`. Built-in commands (`help`, `tasks`, `model:`, `recall:`, `note:`, etc.) are handled locally with no LLM call. Everything else goes to `llm.chat()`.

**Three-layer LLM context** (assembled by `_build_context()` in `agent.py`):
- Layer 1 (system prompt): `IDENTITY.md` + all `skills/*.md` concatenated
- Layer 2 (relevant memories): top 5 semantic search results from `memory.search()`
- Layer 3 (recent history): last 15 turns from `memory.get_recent()`

**Agentic file-read loop:** After an LLM response, `agent.py` checks for `[READ_FILE: path]` and calls the model again with the file contents (up to 3 iterations). Allowed read paths: `skills/`, `tasks/`, `data/usage.log`.

**LLM-generated file writes:** The agent detects `[SAVE_SKILL: name.md]` / `[SAVE_TASK: name.py]` / `[SAVE_NOTE: project]` blocks in LLM responses. Skills and tasks require user confirmation (`yes`/`no`); notes are saved immediately.

## Key Modules

| Module | Role |
|--------|------|
| `agent.py` | Entry point, command dispatcher, context builder, socket server |
| `config.py` | `.env` loader; all settings accessed as `config.VARNAME` |
| `llm.py` | OpenRouter API calls; logs token usage to `data/usage.log` |
| `memory.py` | SQLite-backed memory store with three search tiers: sqlite-vec KNN → numpy cosine → FTS5 |
| `scheduler.py` | Discovers and runs `tasks/*.py` on schedule; supports hot-reload via `scheduler.reload()` |
| `orchestrator.py` | `ensemble:` command — runs specialist subagents in parallel threads, synthesises into one reply |
| `telegram_bot.py` | Telegram polling gateway (async via `python-telegram-bot`) |
| `email_bot.py` | IMAP polling + SMTP reply gateway |
| `notify.py` | Shared utility for tasks: `from notify import send` — prints to terminal and sends to Telegram |
| `transcribe.py` | Voice message transcription via `faster-whisper` |
| `onboarding.py` | First-run setup (tkinter GUI or terminal prompts) |
| `IDENTITY.md` | Agent persona / system prompt (loaded at runtime, not compiled) |

## Tasks

Tasks are `tasks/*.py` scripts with a metadata header. The scheduler loads the project root onto `sys.path` automatically, so tasks can `import config`, `import memory`, `from notify import send`, etc. without path setup.

**Header format:**
```python
# TASK: Human Readable Name
# SCHEDULE: every day at 08:00   # or: every hour / every 30 minutes / on demand
# ENABLED: false
# DESCRIPTION: What this task does
```

**Sending notifications from tasks** — always use `notify.send()`, not a local helper:
```python
from notify import send
send("Your message here")  # prints to terminal AND sends to Telegram
```

**Calling the LLM from a task** — use `requests` directly with `config.OPENROUTER_API_KEY`; see `tasks/daily_quote.py` for the pattern.

Tasks with `SCHEDULE: on demand` never run automatically — triggered via `run task: <name>` from terminal or Telegram.

## Skills

Skills are `skills/*.md` markdown files concatenated into the system prompt at startup. Changes require an agent restart. The `how_to_write_a_skill.md` file defines the format for the agent to self-author new skills.

## Configuration

All settings live in `.env` (gitignored). Use `config.py` constants — never `os.environ` directly — in any module.

Key `.env` variables:
- `OPENROUTER_API_KEY` (required)
- `OPENROUTER_MODEL` — changed at runtime with `model: <id>` command; persisted back to `.env`
- `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_ALLOWED_USERS`
- `EMAIL_IMAP_HOST` — leave blank to disable email gateway
- `WEATHER_LOCATION` — city name or `lat,lon` for weather task

## Memory

`data/memory.db` stores two tables:
- `memories` — long-term memory (conversations, notes, ingested documents); searched semantically
- `conversation` — recent turns fed directly into every LLM call

Memory roles: `conversation`, `note` (keyed by `source` = project name), `document` (ingested URLs/PDFs). The `recall: todo` command filters notes by role and project; only notes starting with `[ ]` are shown by default.

## Telegram Access Control

`TELEGRAM_ALLOWED_USERS` is a comma-separated list of numeric user IDs. Leave it empty to allow anyone — not recommended for public bots.

## systemd Service

```bash
systemctl --user restart molluskai   # apply changes
journalctl --user -u molluskai -f    # live logs
```

Run with `--no-terminal` flag in the service unit. Connect interactively over SSH with `python agent.py --terminal`.
