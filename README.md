# MolluskAI

> A minimal, open-source AI agent for Raspberry Pi 4/5.
> Connects to [OpenRouter](https://openrouter.ai) for LLM access, stores memory locally, and is reachable by terminal or Telegram.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Inspired by [PicoClaw](https://github.com/sipeed/picoclaw).

---

## Features

- **OpenRouter integration** — access Gemini, Claude, GPT, Llama, Mistral, and more with one API key
- **Telegram gateway** — send messages, PDFs, and voice notes from your phone
- **Voice messages** — Telegram voice notes are transcribed locally via Whisper and sent to the agent
- **Vector memory** — conversations and documents stored locally and recalled semantically
- **Skills** — markdown files that teach the agent new behaviours; the agent can write them for you
- **Tasks** — Python scripts that run on a schedule with zero AI API cost; enable/disable without restarting
- **Project notes** — capture ideas by voice, text, or conversation; retrieve by project or theme using semantic search
- **Web monitoring** — ask the agent to generate a daily keyword digest from news RSS, Hacker News, Reddit, or any URL
- **Diet logging** — speak meals into Telegram, the agent estimates calories and sends a morning summary of the previous day
- **Expense tracking** — log purchases by voice or text with automatic categorisation; monthly spending report by category delivered to Telegram
- **Workout log** — log exercise sessions by voice or text; weekly training summary delivered every Monday morning
- **Email gateway** — receive emails via IMAP, auto-reply with the LLM, and forward to a human when needed
- **Low cost** — three-layer context (identity + relevant memories + recent turns) keeps each call to ~3,000 tokens
- **Readable code** — written to be understood and extended; ideal for learning on Raspberry Pi

---

## Download & Install

```bash
wget https://raw.githubusercontent.com/skyl4rk/molluskai/main/install.sh
chmod +x install.sh && ./install.sh
```

The installer clones the repo, creates a virtual environment, and installs all dependencies.

---

## Requirements

- Raspberry Pi 4 or 5 running **Raspberry Pi OS 64-bit** (full desktop for GUI onboarding; Lite works in terminal mode)
- Python 3.9 or later
- An [OpenRouter API key](https://openrouter.ai/keys)
- A Telegram bot token *(optional)* — create one with [@BotFather](https://t.me/BotFather)

---

## Starting MolluskAI

After every reboot, or when opening a new terminal, use these three commands:

```bash
cd ~/molluskai
source venv/bin/activate
python agent.py
```

> **Tip:** If you set up the systemd service (see [Auto-Start on Boot](#auto-start-on-boot)),
> MolluskAI starts automatically after every reboot with no manual steps needed.

---

## First Run

```bash
cd ~/molluskai
source venv/bin/activate
python agent.py
```

On first run (no `.env` file found), the **onboarding setup** launches:

**GUI (desktop):** A window appears with fields for your credentials.

**Terminal (headless/SSH):** You are prompted for each value in sequence.

You will be asked for:

| Field | Required | Where to get it |
|-------|----------|----------------|
| OpenRouter API Key | Yes | [openrouter.ai/keys](https://openrouter.ai/keys) |
| Model | Yes | Choose from the dropdown or type any OpenRouter model ID |
| Telegram Bot Token | Optional | Message [@BotFather](https://t.me/BotFather) on Telegram |
| Your Telegram User ID | Recommended | See below |

Your credentials are saved to `.env` with permissions set to `600` (owner only).

### Finding Your Telegram User ID

Your Telegram **User ID** is a permanent numeric identifier (e.g. `123456789`) — it is **not** your username or display name.

To find it:
1. Open Telegram
2. Search for **@userinfobot**
3. Send it any message (e.g. `/start`)
4. It replies instantly with your numeric ID

The onboarding setup asks for this ID so that only you can send messages to your bot. You can add more allowed IDs later by editing `.env` directly.

> **Note:** The `TELEGRAM_ALLOWED_USERS` field in `.env` accepts a comma-separated list of numeric IDs.
> Example: `TELEGRAM_ALLOWED_USERS=123456789,987654321`

---

## Terminal Commands

| Command | What it does | AI cost |
|---------|-------------|---------|
| `help` or `?` | Show all commands | None |
| `setup` | Re-run the setup wizard | None |
| `skills` | List skill files | None |
| `tasks` | List task files with status | None |
| `run task: <name>` | Run a task immediately on demand | None |
| `enable task: <name>` | Enable a task, reload scheduler | None |
| `disable task: <name>` | Disable a task, reload scheduler | None |
| `model` | Show current model | None |
| `model: <model-id>` | Switch model, saved to .env | None |
| `notes` | List all note projects with counts | None |
| `note: <project> \| <idea>` | Save an idea to a project | None |
| `note: <idea>` | Save an idea to 'general' | None |
| `recall: <project>` | Retrieve all notes for a project | None |
| `recall: <project> \| <theme>` | Search notes by theme | None |
| `search: <topic>` | Search your memory | None |
| `ingest: <url>` | Fetch and store a web page | None |
| `ingest pdf: <path>` | Extract and store a PDF file | None |
| `<bare url>` | Same as `ingest:` | None |
| `exit` or `quit` | Exit the agent | None |
| *anything else* | Sent to the AI | Yes |

---

## Telegram Commands

All terminal commands work over Telegram as plain text messages. In addition:

| Action | How |
|--------|-----|
| Chat with the agent | Send any text message |
| All terminal commands | Type them as text (e.g. `tasks`, `model: ...`) |
| Ingest a PDF | Send the PDF file as an attachment |
| Send a voice message | Record and send a voice note — transcribed automatically |

---

## Changing the Model

Switch models instantly without restarting — from terminal or Telegram:

```
model: anthropic/claude-3-5-haiku
```

The change takes effect immediately and is saved to `.env` so it persists after a restart. Type `model` on its own to see the current model.

The current model is also shown at startup (`MolluskAI ready  •  model: ...`).

To browse available models, use the **Fetch models** button in the onboarding GUI (`setup` command), or visit [openrouter.ai/models](https://openrouter.ai/models).

---

## Creating Skills with AI

A **skill** is a markdown file in `skills/` that tells the agent how to handle a specific type of request. Skills are loaded into the system prompt at startup.

You can ask the agent to write a skill for you. The agent generates the skill content and asks for your confirmation before saving.

### Example

```
you> Create a skill: Any time I send a link to an HTML page,
     convert that page to text and store it in the database.

agent> Here is a skill for automatic URL ingestion.

       ──────────────────────────────
       Ready to save skill: html_ingestion.md
       ──────────────────────────────
       # HTML Page Ingestion

       When the user sends a URL starting with http or https,
       respond by calling:

           ingest: <url>

       The agent will fetch the page, strip HTML, and store the
       text automatically.
       ──────────────────────────────
       Reply yes to save, no to cancel.

you> yes

agent> Saved skill: html_ingestion.md
       Path: skills/html_ingestion.md
```

The skill is live immediately — no restart needed.

You can also write or edit skill files manually in the `skills/` directory with any text editor.

### Included skills

| Skill | What it does |
|-------|-------------|
| `how_to_write_a_skill.md` | Guide for the agent on writing new skills |
| `pdf_ingestion.md` | Instructions for ingesting and querying PDF files |
| `cost_report.md` | Report on AI usage costs from the usage log |
| `idea_capture.md` | Capture and organise ideas by project; retrieve by theme |
| `web_monitor.md` | Generate daily keyword monitoring tasks for news, HN, Reddit, or any URL |
| `diet_log.md` | Log meals by voice or text; agent estimates calories and tracks daily totals |
| `expense_tracker.md` | Log purchases by voice or text with category; monthly spending report by category |
| `workout_log.md` | Log exercise sessions by voice or text; weekly training summary every Monday |

---

## Creating Tasks with AI

A **task** is a Python script in `tasks/` that runs on a schedule without any AI API calls.

Ask the agent to write a task for you. It generates the code with its metadata header and asks for confirmation before saving.

### Example

```
you> Create a task: Search Craigslist for bicycles for sale near
     zip code 34567, under $200, send me the top 10 results to
     Telegram with an HTML link for each one.

agent> Here is a task that does this.

       ──────────────────────────────
       Ready to save task: craigslist_bikes.py
       ──────────────────────────────
       # TASK: Craigslist Bike Search
       # SCHEDULE: every day at 09:00
       # ENABLED: false
       # DESCRIPTION: Search Craigslist for bikes under $200...
       ...
       ──────────────────────────────
       Reply yes to save, no to cancel.

you> yes

agent> Saved task: craigslist_bikes.py
```

After saving, **review the code**, then enable it — no restart needed:

```
enable task: craigslist_bikes
```

> **Review before enabling.** Read through the generated code before enabling, especially for tasks that send messages, access the network, or perform system operations.

If you prefer to edit the file manually, change `# ENABLED: false` to `# ENABLED: true` in the header, then run `enable task: craigslist_bikes` to reload the scheduler without restarting.

---

## Writing Skills and Tasks Manually

### Writing a Skill

Create any `.md` file in `skills/`. Example — `skills/morning_summary.md`:

```markdown
# Morning Summary

When the user says "morning" or asks for a morning briefing:
- Check data/usage.log for yesterday's token count
- Give a 2-sentence summary of any topics discussed yesterday (from memory)
- Keep the response under 5 lines
```

Skills are plain text — edit them in any text editor. Changes take effect on the next agent start.

### Writing a Task

Create a `.py` file in `tasks/` with a metadata header. Example — `tasks/ping_check.py`:

```python
# TASK: Network Ping Check
# SCHEDULE: every 30 minutes
# ENABLED: false
# DESCRIPTION: Pings a host and sends an alert to Telegram if it fails

import subprocess
import requests
import config  # project root is on sys.path automatically

def run():
    result = subprocess.run(["ping", "-c", "1", "8.8.8.8"], capture_output=True)
    if result.returncode != 0:
        if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
            requests.post(
                f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": config.TELEGRAM_CHAT_ID, "text": "Network unreachable!"},
                timeout=5,
            )
```

Supported schedule strings:
- `every day at 08:00`
- `every hour`
- `every 30 minutes`
- `every 10 seconds` *(good for testing)*
- `on demand` *(never auto-runs — triggered manually with `run task: <name>`)*

---

## On-Demand Tasks

Tasks with `SCHEDULE: on demand` never run automatically. They are triggered manually at any time — from Telegram or terminal:

```
run task: df_report
run task: weather_report
```

The task runs immediately in the background and sends its output to Telegram. The `run task:` command works on any task, including scheduled ones.

### Included scheduled tasks

| Task | Schedule | What it does |
|------|----------|-------------|
| `daily_report` | every day at 08:00 | Sends yesterday's AI token usage summary to Telegram |
| `diskfree_report` | every day at 08:00 | Alerts if the main disk exceeds 75% usage |
| `diet_morning_report` | every day at 07:30 | Sends yesterday's food log and calorie total |
| `expense_monthly_report` | 1st of each month | Sends last month's spending grouped by category |
| `workout_weekly_report` | every Monday | Sends last week's training sessions and totals |
| `daily_quote` | every day at 07:00 | Generates a stoic quote and reflection using a specified model |
| `ensemble_insight` | every day at 08:00 | Three models answer a question in parallel; a fourth synthesises the best answer |

All scheduled tasks are disabled by default. Enable with `enable task: <name>`.

### Included on-demand tasks

| Task | What it does |
|------|-------------|
| `df_report` | Sends full `df -h` disk usage output to Telegram |
| `weather_report` | Sends today's weather via [wttr.in](https://wttr.in) (no API key needed) |

To set a location for the weather report, edit `LOCATION` at the top of `tasks/weather_report.py`:

```python
LOCATION = "London"   # or leave blank to auto-detect by IP
```

### Writing your own on-demand task

Ask the agent: *"Create an on-demand task that runs git pull and sends the output to Telegram."*

Or write one manually — use `SCHEDULE: on demand` in the header:

```python
# TASK: Git Pull
# SCHEDULE: on demand
# ENABLED: false
# DESCRIPTION: Runs git pull on the molluskai directory and sends output to Telegram

import subprocess
import requests
import config

def run():
    result = subprocess.run(
        ["git", "pull"],
        capture_output=True, text=True,
        cwd="/home/pi/molluskai"   # adjust to your install path
    )
    output = result.stdout or result.stderr or "No output."
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": output[:4000]},
            timeout=10,
        )
```

---

## Agent Orchestration

The `ensemble:` command routes a question through a panel of specialist subagents — each with a distinct role and model — then passes all their outputs to a synthesiser that produces one final response.

```
ensemble: What are the main risks of adopting AI in a small business?
```

### How it works

1. The main agent acknowledges the request immediately: *"Consulting specialists: Analyst, Devil's Advocate, Pragmatist…"*
2. Three specialist subagents run **in parallel**, each answering from their own perspective:
   - **Analyst** (Gemini Flash) — structured breakdown, key components, assumptions
   - **Devil's Advocate** (Llama 70B) — counterarguments, risks, overlooked consequences
   - **Pragmatist** (Claude Haiku) — practical constraints, concrete next steps
3. A **synthesiser** (Claude Haiku) reads all three outputs and weaves them into one coherent final answer
4. The synthesised response is returned to the user — no raw specialist outputs shown

### Customising the specialists

Edit `orchestrator.py` to change roles, models, or add/remove agents:

```python
SUBAGENTS = [
    {
        "name":  "Historian",
        "model": "google/gemini-2.0-flash-001",
        "role":  "You are a historian. When given a question, provide relevant historical context and precedents...",
    },
    {
        "name":  "Economist",
        "model": "meta-llama/llama-3.3-70b-instruct",
        "role":  "You are an economist. Analyse the question through the lens of incentives, trade-offs, and resource allocation...",
    },
    # add as many as you need
]

SYNTHESISER = {
    "model": "anthropic/claude-3-5-haiku",
    "role":  "You are a synthesis expert...",
}
```

The number of subagents is flexible — threading adjusts automatically.

### Difference from the ensemble_insight task

| | `ensemble:` command | `ensemble_insight` task |
|---|---|---|
| Triggered by | User question | Schedule (daily) |
| Question | Whatever the user asks | Fixed `DAILY_QUESTION` |
| Returns to | User (terminal or Telegram) | Telegram only |
| Purpose | On-demand reasoning | Daily automated insight |

---

## Multi-Model Tasks

Tasks can call the OpenRouter API directly, bypassing the main agent's model. This lets you choose the best (or cheapest) model for each specific job.

### Using a different model in a task

Set `TASK_MODEL` at the top of the task file and call the API directly:

```python
TASK_MODEL = "anthropic/claude-3-5-haiku"

def _ask(prompt):
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"},
        json={"model": TASK_MODEL, "messages": [{"role": "user", "content": prompt}]},
        timeout=60,
    )
    return response.json()["choices"][0]["message"]["content"].strip()
```

See `tasks/daily_quote.py` for a complete working example.

### Running multiple models in parallel

Using Python's `threading` module, a task can call several models simultaneously and combine their responses. The total time is roughly that of the slowest single call rather than the sum of all calls.

### Ensemble tasks

The included `ensemble_insight` task demonstrates the ensemble pattern:

1. **Three panel models** answer the same question simultaneously in parallel threads (Haiku, Gemini, Llama)
2. Their answers are assembled into a synthesis prompt
3. **A fourth model** reads all three and produces one refined response
4. Only the synthesis is sent to Telegram

To customise it, edit the top of `tasks/ensemble_insight.py`:

```python
DAILY_QUESTION = "What is one practical thing a person can do today to think more clearly?"

PANEL_MODELS = [
    ("Haiku",  "anthropic/claude-3-5-haiku"),
    ("Gemini", "google/gemini-2.0-flash-001"),
    ("Llama",  "meta-llama/llama-3.3-70b-instruct"),
]

SYNTHESISER_MODEL = "anthropic/claude-3-5-haiku"
```

Add or remove entries from `PANEL_MODELS` and the threading adjusts automatically. Test immediately with:

```
run task: ensemble_insight
```

---

## Auto-Start on Boot

Run MolluskAI automatically when the Raspberry Pi boots using a systemd user service.

Before starting, make sure you are in your home directory with the venv deactivated:

```bash
deactivate        # exit the virtual environment if active
cd ~              # return to home directory
```

### 1. Create the service file

> **Note:** `~/.config/systemd/user` is the standard systemd path — `user` is a literal
> directory name, not a placeholder. The `~` expands to your home directory automatically.

```bash
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/molluskai.service
```

Paste this content — **replace `/home/pi/` with your actual home directory path**
(e.g. `/home/historian/`). Run `echo $HOME` if you're not sure what it is.

```ini
[Unit]
Description=MolluskAI Agent
After=network.target

[Service]
# Replace /home/pi/ with your actual home directory (e.g. /home/historian/)
WorkingDirectory=/home/pi/molluskai
ExecStart=/home/pi/molluskai/venv/bin/python agent.py --no-terminal

Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

### 2. Enable and start the service

Replace `pi` with your actual username in the `loginctl` command:

```bash
systemctl --user enable molluskai
systemctl --user start molluskai
sudo loginctl enable-linger pi
```

`loginctl enable-linger` allows user services to run without an active login session (i.e., after a reboot with no one logged in).

### 3. Manage the service

```bash
systemctl --user status molluskai      # Check if running
systemctl --user stop molluskai        # Stop
systemctl --user restart molluskai     # Restart (e.g. after changing .env or adding tasks)
journalctl --user -u molluskai -f      # Watch live logs
```

The `--no-terminal` flag runs the agent headlessly — Telegram and scheduler only, no terminal prompt.

---

## Security

### Credentials (`.env` file)

All API keys are stored in `.env`. This file is created with `chmod 600` (only the owner can read or write it) automatically by the setup. It is excluded from git via `.gitignore`.

- Never share your `.env` file
- Never commit it to a public repository
- If you suspect a key is compromised, rotate it at [openrouter.ai/keys](https://openrouter.ai/keys) or via @BotFather

### Telegram Access Control

Only Telegram users listed in `TELEGRAM_ALLOWED_USERS` (in `.env`) can interact with the bot. Any message from an unlisted user ID receives:

> *"Sorry, I'm a private assistant. Access is not permitted."*

Find your numeric Telegram user ID by messaging [@userinfobot](https://t.me/userinfobot) — it replies with a number like `123456789`. This is **not** your username or display name.

If `TELEGRAM_ALLOWED_USERS` is left empty, **all users can interact** with the bot — not recommended.

### What the Agent Can and Cannot Do

| Action | Agent (LLM) | Tasks (scripts) |
|--------|-------------|-----------------|
| Read/write `skills/` and `tasks/` | Yes (with confirmation) | Yes |
| Read/write `data/` (memory DB, logs) | Yes | Yes |
| Run shell commands | **No** | Yes (use with caution) |
| Reboot the device | **No** | Yes (if scripted) |
| Modify system files | **No** | Yes (if scripted) |
| Accept messages from anyone on Telegram | **No** | N/A |

Tasks can be enabled via the `enable task: <name>` command or by editing the file header — the LLM cannot enable tasks on its own.

### Network Exposure

MolluskAI uses Telegram **polling** (outbound requests from the Pi to Telegram's servers). It does not open any listening ports. Your Raspberry Pi does not need to be exposed to the internet.

---

## Uninstalling

### 1. Stop and remove the service (if enabled)

```bash
systemctl --user stop molluskai
systemctl --user disable molluskai
rm ~/.config/systemd/user/molluskai.service
systemctl --user daemon-reload
```

### 2. Delete the project directory

```bash
# Replace /home/pi/molluskai with your actual install path
rm -rf /home/pi/molluskai
```

This removes everything: the code, the memory database, the usage log, and the `.env` credentials.

### 3. Remove the installer script (if used)

If you installed using the one-line wget method, the `install.sh` script remains in the directory where you ran it (usually your home directory):

```bash
rm ~/install.sh
```

### 4. Revoke API keys (recommended)

- **OpenRouter:** Go to [openrouter.ai/keys](https://openrouter.ai/keys) and delete the key
- **Telegram:** Message @BotFather and send `/deletebot`

---

## Project Structure

```
molluskai/
├── agent.py           # Entry point and main loop
├── config.py          # Settings loader (.env → module constants)
├── llm.py             # OpenRouter API calls and usage logging
├── memory.py          # Vector memory (sqlite-vec + fastembed, with fallbacks)
├── onboarding.py      # First-run setup (tkinter GUI or terminal prompts)
├── telegram_bot.py    # Telegram polling gateway
├── scheduler.py       # Task discovery and scheduling
├── transcribe.py      # Voice message transcription (faster-whisper)
├── IDENTITY.md        # Agent persona / system prompt
├── skills/            # AI prompt templates (markdown, edit freely)
│   ├── how_to_write_a_skill.md
│   ├── pdf_ingestion.md
│   └── cost_report.md
├── tasks/             # Local automation scripts (Python, edit freely)
│   ├── README.md
│   └── daily_report.py
├── data/              # Database and logs (auto-created, not committed)
│   ├── memory.db
│   └── usage.log
├── .env               # Your credentials (never committed)
├── .env.example       # Template
├── .gitignore
├── LICENSE            # MIT
├── FEASIBILITY.md     # Project feasibility analysis
├── IMPLEMENTATION.md  # Implementation notes
└── requirements.txt
```

---

## How Memory Works

Every conversation is stored in `data/memory.db` (SQLite). When you send a message:

1. Your message is embedded locally using `BAAI/bge-small-en-v1.5` (~24MB, runs on-device)
2. The 5 most relevant past memories are retrieved
3. The last 15 conversation turns are included
4. Everything is assembled into a ~3,000-token prompt
5. The response is stored as a new memory

Use `search: <topic>` to retrieve memories on demand.

**Ingesting documents:**
```
ingest: https://example.com/article
ingest pdf: /home/pi/documents/report.pdf
```

---

## Project Notes

MolluskAI includes a lightweight idea capture system for organising thoughts around ongoing projects — a book, research topic, recipe collection, or anything else you return to over time.

### Saving ideas

From terminal or Telegram — type or speak:

```
note: book | The lighthouse is a metaphor for the character's isolation
note: recipes | Add preserved lemon to the chicken tagine
note: book | The antagonist needs a clearer motivation in chapter 3
```

Omitting the project saves to `general`:
```
note: Remember to check the sunset time for the garden scene
```

The agent also captures ideas automatically mid-conversation. If you say *"book idea: the ending should mirror the opening scene"*, the agent saves it as a note and confirms without interrupting the flow.

Voice messages work the same way — speak the idea on Telegram, it is transcribed and saved.

### Retrieving notes

```
notes                          ← list all projects and note counts
recall: book                   ← all book notes, newest first
recall: book | character       ← notes most relevant to 'character'
recall: book | chapter endings ← notes about endings
```

The `recall: project | theme` form uses semantic search — it finds notes by meaning, not just matching words.

---

## Voice Messages (Telegram)

You can send voice messages to the bot on Telegram and it will transcribe them using [faster-whisper](https://github.com/SYSTRAN/faster-whisper) before passing them to the agent.

### Setup

1. Install ffmpeg (required for audio decoding):
   ```bash
   sudo apt install ffmpeg
   ```

2. Install faster-whisper (already in `requirements.txt`):
   ```bash
   pip install faster-whisper
   ```

On first use, the Whisper `tiny` model (~40MB) is downloaded automatically to `~/.cache/huggingface/hub/`.

### How it works

1. Send a voice message to the bot on Telegram
2. The bot replies `Transcribing…`
3. Once transcribed, it shows `_(Heard: your words here)_` so you can verify
4. The agent responds to the transcribed text as normal

### Changing the model

If you want better accuracy at the cost of speed, edit `transcribe.py` and change:

```python
WHISPER_MODEL = "tiny"   # change to "base" or "small"
```

| Model | Size | Notes |
|-------|------|-------|
| tiny  | ~39MB | Fastest, good for clear speech |
| base  | ~74MB | Better accuracy, ~2× slower on Pi |
| small | ~244MB | Best quality, noticeably slow on Pi 4 |

---

## Web Monitoring

Ask the agent to generate a daily keyword digest delivered to Telegram. No API keys required.

Supported sources:

| Source | Example request |
|--------|----------------|
| News / RSS feeds | *"Monitor BBC tech news for 'raspberry pi'"* |
| Hacker News | *"Daily HN digest for 'machine learning'"* |
| Reddit | *"Watch r/selfhosted for 'home server'"* |
| Any URL | *"Alert me when 'planning application' appears on my council website"* |

The agent generates a task script, you review and enable it:

```
enable task: hn_monitor_machine_learning
```

The report arrives at the scheduled time each day via Telegram.

---

## Diet Logging

Track food intake and estimate calories by speaking into Telegram or typing naturally.

### Logging a meal

Just describe what you ate — by voice or text:

```
I had two eggs and toast for breakfast
just ate a banana and a coffee
lunch was a chicken salad
```

The agent identifies the food, estimates calories using standard nutritional values, saves the entry, and replies with the estimate:

```
agent> Logged. 2 scrambled eggs + 2 slices toast with butter — roughly 420 kcal.
```

### Enabling the morning summary

A pre-built task sends yesterday's full log to Telegram each morning. Enable it once:

```
enable task: diet_morning_report
```

At 07:30 each day you receive a message like:

```
Diet log for 2026-02-20:

• 2026-02-20 08:15 | 2 scrambled eggs, 2 slices toast with butter | ~420 kcal
• 2026-02-20 13:00 | chicken salad, no dressing | ~250 kcal
• 2026-02-20 19:30 | pasta with tomato sauce (200g cooked) | ~300 kcal

Total: ~970 kcal
```

No message is sent if nothing was logged the previous day.

### Checking the running total

```
recall: diet
```

This retrieves all diet notes from memory. The agent can sum the calorie values on request.

---

## Expense Tracking

Log purchases by voice or text throughout the day. A scheduled task sends a monthly spending report grouped by category to Telegram on the 1st of each month.

### Logging an expense

Speak or type naturally:

```
spent £12 on lunch
paid 45 for groceries at Tesco
electricity bill was 120
coffee, 3.50
```

The agent categorises the purchase and replies with a confirmation:

```
agent> Logged. 12.00 — eating out.
```

Standard categories: groceries, eating out, transport, utilities, household, health, entertainment, clothing, travel, other.

### Enabling the monthly report

```
enable task: expense_monthly_report
```

On the 1st of each month at 08:00 you receive:

```
Expenses — January 2026

Eating Out: 87.50
  • lunch at the deli — 12.00
  • pizza Friday — 24.50
  • coffee runs — 51.00
Groceries: 210.00
  • Tesco weekly — 45.00
  • Tesco weekly — 48.00
  ...
Transport: 32.00
  • bus fares — 22.00
  • parking — 10.00

Total: 329.50
```

No message is sent if nothing was logged the previous month.

### Checking spending so far this month

```
recall: expenses
```

Retrieves all expense notes. Ask the agent to total by category from the results shown.

---

## Workout Log

Log exercise sessions by voice or text. A scheduled task sends a weekly summary every Monday morning covering the previous week.

### Logging a session

Speak or type naturally after your workout:

```
just finished a 5k run, 28 minutes
did chest day — bench 3 sets of 10 at 80kg, incline dumbbell 3 sets of 8
45 minute yoga session
walked 4 miles this morning
```

The agent identifies the type, logs the details, and replies with a confirmation. Personal bests and milestones are noted automatically.

Supported types: strength, cardio, hiit, walk, cycle, swim, flexibility, sport, other.

### Enabling the weekly report

```
enable task: workout_weekly_report
```

Every Monday at 08:00 you receive a summary of the previous week:

```
Workouts — 10 Feb – 16 Feb 2026
Trained: 5/7 days  •  Rest: 2

Monday 10 Feb
  [cardio] morning run
  5.2 km in 28 min

Wednesday 12 Feb
  [strength] chest and shoulders
  bench press 3x10@80kg, OHP 3x8@50kg

Thursday 13 Feb
  [walk] lunchtime walk
  3.5 km, 40 min

Saturday 15 Feb
  [strength] legs
  squat 4x5@100kg, Romanian deadlift 3x10@70kg

Sunday 16 Feb
  [flexibility] yoga flow
  45 min vinyasa

Session types: cardio: 1, flexibility: 1, strength: 2, walk: 1
```

No message is sent if no workouts were logged the previous week.

### Reviewing recent training

```
recall: workouts
```

Retrieves logged sessions. Ask the agent to identify patterns, flag rest days, or suggest what to focus on next.

---

## Email Gateway

MolluskAI can monitor an email inbox, respond to messages with the LLM, and forward emails to a human when needed — with no open ports and no webhooks.

### How it works

1. The agent polls your inbox via IMAP every 60 seconds (configurable)
2. Each new email is passed to the agent as a message
3. The agent composes a professional auto-reply
4. If the email needs human attention, the agent includes a forwarding instruction in its response — the email is forwarded automatically and the directive is stripped from the customer-facing reply

### Setup

Add the following to your `.env` file:

```
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_IMAP_USER=you@gmail.com
EMAIL_IMAP_PASSWORD=your-app-password

EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=you@gmail.com
EMAIL_SMTP_PASSWORD=your-app-password

EMAIL_POLL_INTERVAL=60
EMAIL_ALLOWED_FROM=
```

Leave `EMAIL_IMAP_HOST` blank to disable the email gateway entirely.

#### Gmail setup

1. Enable IMAP: Gmail Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP
2. Create an App Password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) (requires 2-step verification to be on)
3. Use the App Password as `EMAIL_IMAP_PASSWORD` and `EMAIL_SMTP_PASSWORD` — not your regular Gmail password

#### Other providers

| Provider | IMAP host | SMTP host |
|----------|-----------|-----------|
| Gmail | `imap.gmail.com` | `smtp.gmail.com` |
| Outlook / Hotmail | `imap.outlook.com` | `smtp.office365.com` |
| Yahoo | `imap.mail.yahoo.com` | `smtp.mail.yahoo.com` |
| Any standard provider | Check provider docs | Check provider docs |

### Configuring the forwarding address

Edit `skills/email_handler.md` and set your forwarding address:

```
**Default forward: `sales@yourcompany.com`**
```

The agent uses this address when it decides an email needs human follow-up (customer inquiries, support requests, etc.).

### Sender whitelist

`EMAIL_ALLOWED_FROM` is a comma-separated list of email addresses allowed to contact the agent. Leave it blank to accept emails from anyone — appropriate for a customer-facing inbox.

```
EMAIL_ALLOWED_FROM=trusted@example.com,partner@example.com
```

### How the forwarding directive works

The agent includes a special tag in its response when forwarding is needed:

```
[FORWARD_EMAIL: sales@yourcompany.com]
Customer inquiry about bulk pricing from John Smith.
[/FORWARD_EMAIL]
```

The gateway strips this from the reply sent to the customer, sends the auto-reply, and sends a separate forwarded email to `sales@yourcompany.com`. The customer only sees the professional auto-reply.

### Response time

Emails are checked every `EMAIL_POLL_INTERVAL` seconds (default: 60). Auto-replies are not instant — document this expectation in your auto-reply text if needed.

---

## Troubleshooting

**`sqlite-vec` won't install on ARM64**
```bash
sudo apt install gcc make libsqlite3-dev
pip install sqlite-vec
```
The agent still works without it — it falls back to numpy automatically.

**`fastembed` is slow on first run**
It downloads the embedding model (~24MB) once. All subsequent starts are fast.

**Telegram bot not responding**
- Check `TELEGRAM_TOKEN` is set in `.env`
- Check your Telegram user ID is in `TELEGRAM_ALLOWED_USERS`
- Run `systemctl --user status molluskai` to check for errors

**`No module named 'tkinter'`**
```bash
sudo apt install python3-tk
```
Or just run `python agent.py` anyway — it falls back to terminal prompts.

**`(venv)` not shown / module not found after reboot**
Use the standard startup sequence:
```bash
cd ~/molluskai
source venv/bin/activate
python agent.py
```
Or set up the systemd service so it starts automatically on every reboot.

---

## Contributing

MolluskAI is open source under the [MIT License](LICENSE). Contributions are welcome.

- Open issues and pull requests on GitHub
- Share your skills and tasks with the community
- Keep code readable — this is a learning platform project

---

## License

MIT — see [LICENSE](LICENSE).
