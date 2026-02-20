# MolluskAI

> A minimal, open-source AI agent for Raspberry Pi 4/5.
> Connects to [OpenRouter](https://openrouter.ai) for LLM access, stores memory locally, and is reachable by terminal or Telegram.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Inspired by [PicoClaw](https://github.com/sipeed/picoclaw).

---

## Features

- **OpenRouter integration** — access Gemini, Claude, GPT, Llama, Mistral, and more with one API key
- **Telegram gateway** — send and receive messages from your phone, send PDF files to ingest
- **Vector memory** — conversations and documents stored locally and recalled semantically
- **Skills** — markdown files that teach the agent new behaviours; the agent can write them for you
- **Tasks** — Python scripts that run on a schedule with zero AI API cost
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
| `enable task: <name>` | Enable a task, reload scheduler | None |
| `disable task: <name>` | Disable a task, reload scheduler | None |
| `model` | Show current model | None |
| `model: <model-id>` | Switch model, saved to .env | None |
| `search: <topic>` | Search your memory | None |
| `ingest: <url>` | Fetch and store a web page | None |
| `ingest pdf: <path>` | Extract and store a PDF file | None |
| `<bare url>` | Same as `ingest:` | None |
| `exit` or `quit` | Exit the agent | None |
| *anything else* | Sent to the AI | Yes |

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

After saving, **enable the task** by editing the file:

```bash
nano tasks/craigslist_bikes.py
# Change:  # ENABLED: false
# To:      # ENABLED: true
```

Then restart the agent so the scheduler picks it up:

```bash
# Terminal mode (activate venv first if you used one)
cd ~/molluskai
source venv/bin/activate
python agent.py

# If running as a service
systemctl --user restart molluskai
```

> **Review before enabling.** Read through the generated code before setting ENABLED: true, especially for tasks that send messages, access the network, or perform system operations.

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

import sys, os, subprocess
from pathlib import Path
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

def run():
    import requests
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")

    result = subprocess.run(["ping", "-c", "1", "8.8.8.8"], capture_output=True)
    if result.returncode != 0:
        token   = os.getenv("TELEGRAM_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        if token and chat_id:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": "Network unreachable!"},
                timeout=5,
            )

if __name__ == "__main__":
    run()
```

Supported schedule strings:
- `every day at 08:00`
- `every hour`
- `every 30 minutes`
- `every 10 seconds` *(good for testing)*

---

## Auto-Start on Boot

Run MolluskAI automatically when the Raspberry Pi boots using a systemd user service.

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

Tasks that perform system actions must be **manually enabled** by editing the file header. The LLM cannot enable tasks.

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

### 3. Revoke API keys (recommended)

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
