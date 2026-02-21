# agent.py — MolluskAI entry point and core agent loop
#
# Usage:
#   python agent.py                  # terminal + telegram + scheduler
#   python agent.py --no-terminal    # headless: telegram + scheduler only
#
# On first run (no .env found), the onboarding setup is shown.
# After that, the agent starts all components and enters the main loop.

import re
import sys
import textwrap
from pathlib import Path

PROJECT_DIR = Path(__file__).parent

# Tracks a pending skill or task file write awaiting user confirmation.
# Set when the LLM response contains a [SAVE_SKILL:...] or [SAVE_TASK:...] block.
_pending_write: dict = {}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    no_terminal = "--no-terminal" in sys.argv

    # Step 1 — Onboarding: run if .env is missing or incomplete
    import config
    if not config.is_configured():
        import onboarding
        onboarding.run()
        # Re-import config so it picks up the newly written .env values
        import importlib
        importlib.reload(config)

    # Step 2 — Initialise the memory database
    import memory
    memory.init()

    # Step 3 — Start the task scheduler (background daemon thread)
    import scheduler
    scheduler.start()

    # Step 4 — Start Telegram gateway (background daemon thread, if token set)
    import telegram_bot
    telegram_bot.start(handle_message)

    # Step 5 — Run terminal loop (or wait headlessly)
    if no_terminal:
        import time
        print("[agent] Running headless. Use Telegram to interact. Ctrl+C to stop.")
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n[agent] Stopped.")
    else:
        _terminal_loop()


# ---------------------------------------------------------------------------
# Central message dispatcher
# ---------------------------------------------------------------------------

def handle_message(text: str, reply_fn) -> None:
    """
    Process one message from any source (terminal or Telegram).

    text:     The user's input string.
    reply_fn: A callable that sends a response string to the user.

    Built-in commands are handled locally (no LLM call, no cost).
    Everything else is sent to the LLM with a three-layer context.
    """
    global _pending_write
    import memory
    import llm

    text = text.strip()
    if not text:
        return

    lower = text.lower()

    # --- Pending file-write confirmation ---
    # When the LLM has proposed saving a skill or task file, the next message
    # from the user is treated as confirmation ("yes") or cancellation ("no").
    if _pending_write:
        if lower in ("yes", "y", "confirm"):
            path    = Path(_pending_write["path"])
            content = _pending_write["content"]
            ftype   = _pending_write["type"]
            _pending_write = {}
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            reply_fn(f"Saved {ftype}: {path.name}\nPath: {path}")
        elif lower in ("no", "n", "cancel"):
            ftype = _pending_write.get("type", "file")
            _pending_write = {}
            reply_fn(f"Cancelled — {ftype} was not saved.")
        else:
            # Not a yes/no — clear the pending write and handle normally
            _pending_write = {}
            reply_fn("Pending save cancelled (new message received). Send your message again if needed.")
        return

    # --- Built-in commands (no LLM call) ---

    if lower in ("help", "?"):
        reply_fn(_help_text())
        return

    if lower == "setup":
        reply_fn("Re-running setup. Restart the agent after saving to apply changes.")
        import onboarding
        onboarding.run()
        return

    if lower == "skills":
        reply_fn(_list_skills())
        return

    if lower == "tasks":
        reply_fn(_list_tasks())
        return

    if lower == "model":
        import config
        reply_fn(f"Current model: {config.OPENROUTER_MODEL}\nUsage: model: <model-id>")
        return

    if lower.startswith("model:"):
        model_id = text[6:].strip()
        if not model_id:
            import config
            reply_fn(f"Current model: {config.OPENROUTER_MODEL}\nUsage: model: <model-id>")
            return
        import config
        config.set_model(model_id)
        reply_fn(f"Model changed to: {model_id}\nSaved to .env — no restart needed.")
        return

    if lower == "notes":
        reply_fn(_list_note_projects())
        return

    if lower.startswith("note:"):
        body = text[5:].strip()
        if "|" in body:
            project, content = body.split("|", 1)
            project = project.strip()
            content = content.strip()
        else:
            project = "general"
            content = body
        if not content:
            reply_fn("Usage: note: <project> | <idea>  or  note: <idea>")
            return
        import memory
        memory.store_memory(content, role="note", source=project)
        reply_fn(f"Note saved to '{project}'.")
        return

    if lower.startswith("recall:"):
        body = text[7:].strip()
        if "|" in body:
            project, query = body.split("|", 1)
            project = project.strip()
            query   = query.strip()
        else:
            project = body.strip()
            query   = None
        if not project:
            reply_fn("Usage: recall: <project>  or  recall: <project> | <theme>")
            return
        import memory
        notes = memory.get_notes(project, query=query)
        reply_fn(_format_notes(project, notes, query))
        return

    if lower.startswith("run task:"):
        reply_fn(_run_task_now(text[9:].strip()))
        return

    if lower.startswith("enable task:"):
        reply_fn(_set_task_enabled(text[12:].strip(), True))
        return

    if lower.startswith("disable task:"):
        reply_fn(_set_task_enabled(text[13:].strip(), False))
        return

    if lower.startswith("search:"):
        query = text[7:].strip()
        if not query:
            reply_fn("Usage: search: <topic>")
            return
        results = memory.search(query, n=6)
        reply_fn(_format_search_results(results, query))
        return

    if lower.startswith("ingest:"):
        url = text[7:].strip()
        if not url:
            reply_fn("Usage: ingest: <url>")
            return
        reply_fn(memory.ingest_url(url))
        return

    if lower.startswith("ingest pdf:"):
        path = text[11:].strip()
        reply_fn(memory.ingest_pdf(path))
        return

    # Internal command used by the Telegram PDF handler
    if text.startswith("ingest_pdf:"):
        path = text[11:].strip()
        reply_fn(memory.ingest_pdf(path))
        return

    # Auto-detect bare URLs — ingest them without an explicit command
    if lower.startswith("http://") or lower.startswith("https://"):
        reply_fn(memory.ingest_url(text))
        return

    # --- LLM call ---
    system, messages = _build_context(text)

    try:
        response = llm.chat(messages, system)
    except Exception as e:
        reply_fn(f"Error contacting OpenRouter: {e}")
        return

    # Store both sides of the exchange in the conversation table
    memory.store_conversation("user", text)
    memory.store_conversation("assistant", response)

    # Also store as a searchable long-term memory
    memory.store_memory(
        f"User: {text}\nAssistant: {response}",
        role="conversation",
    )

    # Check if the LLM wants to save a note directly to memory
    cleaned_response, note = _extract_note_directive(response)
    if note:
        memory.store_memory(note["content"], role="note", source=note["project"])
        reply_fn(cleaned_response + f"\n\n_(Note saved to '{note['project']}')_")
        return

    # Check if the LLM wants to write a skill or task file
    cleaned_response, pending = _extract_save_directive(response)
    if pending:
        _pending_write.update(pending)
        reply_fn(cleaned_response)
    else:
        reply_fn(response)


# ---------------------------------------------------------------------------
# Three-layer context builder
# ---------------------------------------------------------------------------

def _build_context(user_message: str) -> tuple:
    """
    Assemble the prompt context for an LLM call.

    Returns (system_prompt: str, messages: list)

    Layer 1 — System prompt  (~400 tokens, fixed per session)
        IDENTITY.md + all skills/*.md concatenated.
        Tells the model who it is and what behaviours to apply.

    Layer 2 — Relevant memories  (~500 tokens, dynamic)
        Top 5 semantically similar past entries from the memory store.
        Injected as a system message so the model can reference past context
        without the full conversation history.

    Layer 3 — Recent conversation  (~2000 tokens, sliding window)
        Last 15 turns from this and previous sessions.
        Provides short-term conversational continuity.

    OpenRouter's middle-out transform (set in llm.py) acts as a safety net:
    if the total context exceeds the model's window, OpenRouter trims the
    middle of the messages list rather than returning an error.
    """
    import memory

    # Layer 1: identity + all skill instructions
    identity    = _load_file(PROJECT_DIR / "IDENTITY.md",
                             fallback="You are a helpful assistant.")
    skills_text = _load_skills()
    system_parts = [identity]
    if skills_text:
        system_parts.append("--- Skills ---\n" + skills_text)
    system = "\n\n".join(system_parts)

    # Layer 2: relevant past memories as an additional system message
    messages = []
    relevant = memory.search(user_message, n=5)
    if relevant:
        mem_block = _format_memories(relevant)
        messages.append({
            "role":    "system",
            "content": f"Relevant memories from previous conversations:\n{mem_block}",
        })

    # Layer 3: recent conversation turns
    messages.extend(memory.get_recent(n=15))

    # The current user message
    messages.append({"role": "user", "content": user_message})

    return system, messages


# ---------------------------------------------------------------------------
# File and skill loaders
# ---------------------------------------------------------------------------

def _load_file(path: Path, fallback: str = "") -> str:
    """Read a file and return its content, or fallback if missing."""
    if path.exists():
        return path.read_text().strip()
    return fallback


def _load_skills() -> str:
    """Concatenate all .md files in skills/ into one string."""
    skills_dir = PROJECT_DIR / "skills"
    if not skills_dir.exists():
        return ""
    parts = [
        f.read_text().strip()
        for f in sorted(skills_dir.glob("*.md"))
        if f.read_text().strip()
    ]
    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Command response formatters
# ---------------------------------------------------------------------------

def _list_skills() -> str:
    skills_dir = PROJECT_DIR / "skills"
    if not skills_dir.exists():
        return "No skills directory found. Create skills/*.md files to add skills."
    files = sorted(skills_dir.glob("*.md"))
    if not files:
        return "No skills found. Add .md files to the skills/ directory."
    lines = ["Skills (AI prompt templates in skills/):"]
    for f in files:
        # Use the first heading line as the skill name
        first = f.read_text().split("\n")[0].lstrip("# ").strip()
        lines.append(f"  • {f.stem}: {first}")
    return "\n".join(lines)


def _list_tasks() -> str:
    import scheduler
    tasks = scheduler.discover_tasks()
    if not tasks:
        return "No tasks found. Add .py files to the tasks/ directory."
    lines = ["Tasks (local automation in tasks/):"]
    for t in tasks:
        status   = "enabled" if t["enabled"] else "disabled"
        sched    = t["schedule"] or "no schedule set"
        desc     = t["description"] or t["name"]
        filename = Path(t["path"]).stem
        lines.append(f"  • {filename} [{status}]  {sched}")
        lines.append(f"    {t['name']} — {desc}")
    return "\n".join(lines)


def _list_note_projects() -> str:
    import memory
    projects = memory.get_note_projects()
    if not projects:
        return (
            "No notes saved yet.\n"
            "Usage: note: <project> | <idea>\n"
            "Example: note: book | The lighthouse represents isolation"
        )
    lines = ["Note projects:"]
    for project, count in projects:
        lines.append(f"  • {project}  ({count} note{'s' if count != 1 else ''})")
    lines.append("\nUse 'recall: <project>' to retrieve notes.")
    return "\n".join(lines)


def _format_notes(project: str, notes: list, query: str = None) -> str:
    if not notes:
        msg = f"No notes found for project '{project}'."
        if query:
            msg += f"\nTry 'recall: {project}' without a theme to see all notes."
        return msg
    header = f"Notes — {project}"
    if query:
        header += f"  (theme: {query})"
    lines = [f"{header}  [{len(notes)} note{'s' if len(notes) != 1 else ''}]",
             "─" * 44]
    for i, n in enumerate(notes, 1):
        ts = (n.get("timestamp") or "")[:16]
        lines.append(f"\n[{i}] {ts}")
        lines.append(n["content"])
    return "\n".join(lines)


def _run_task_now(name: str) -> str:
    """Trigger a task immediately regardless of its schedule."""
    import scheduler
    import threading
    tasks = scheduler.discover_tasks()

    match = None
    for t in tasks:
        if (t["name"].lower() == name.lower() or
                Path(t["path"]).stem.lower() == name.lower()):
            match = t
            break

    if not match:
        available = ", ".join(Path(t["path"]).stem for t in tasks) or "none"
        return f"Task '{name}' not found.\nAvailable tasks: {available}"

    path = Path(match["path"])
    threading.Thread(target=scheduler.run_task, args=(path,), daemon=True).start()
    return f"Running {path.stem}…"


def _set_task_enabled(name: str, enabled: bool) -> str:
    """Edit a task file's ENABLED header and reload the scheduler."""
    import scheduler
    tasks = scheduler.discover_tasks()

    # Match by task name (from header) or file stem, case-insensitive
    match = None
    for t in tasks:
        if (t["name"].lower() == name.lower() or
                Path(t["path"]).stem.lower() == name.lower()):
            match = t
            break

    if not match:
        available = ", ".join(Path(t["path"]).stem for t in tasks) or "none"
        return f"Task '{name}' not found.\nAvailable tasks: {available}"

    path = Path(match["path"])
    content = path.read_text()
    new_content = re.sub(
        r'^(#\s*ENABLED:\s*).*$',
        lambda m: m.group(1) + ("true" if enabled else "false"),
        content,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    if new_content == content:
        return f"Task '{name}' has no ENABLED header — cannot modify."

    path.write_text(new_content)
    scheduler.reload()

    action = "enabled" if enabled else "disabled"
    return f"Task '{Path(match['path']).stem}' {action} and scheduler reloaded."


def _format_memories(results: list) -> str:
    """Format memories for LLM injection — brief and structured."""
    lines = []
    for r in results:
        ts     = (r.get("timestamp") or "")[:16]
        source = f" [{r['source']}]" if r.get("source") else ""
        header = f"[{ts}{source}]" if (ts or source) else ""
        # Truncate to 300 chars to keep context lean
        lines.append(f"{header} {r['content'][:300]}")
    return "\n".join(lines)


def _format_search_results(results: list, query: str) -> str:
    """Format memory search results for display to the user."""
    if not results:
        return f"No memories found for: '{query}'"
    lines = [f"Search results for '{query}':"]
    for i, r in enumerate(results, 1):
        ts     = (r.get("timestamp") or "")[:16]
        source = f"  source: {r['source']}" if r.get("source") else ""
        role   = r.get("role", "")
        lines.append(f"\n[{i}] {ts}  role: {role}{source}")
        lines.append(
            textwrap.fill(
                r["content"][:500],
                width=72,
                initial_indent="  ",
                subsequent_indent="  ",
            )
        )
    return "\n".join(lines)


def _help_text() -> str:
    import config
    return textwrap.dedent(f"""
        MolluskAI — Commands
        ─────────────────────────────────────────
        help / ?            Show this help message
        setup               Re-run the setup wizard (to add Telegram etc.)
        skills              List skill files (AI prompt templates)
        tasks               List task files and their status
        run task: <name>    Run a task immediately (any task, any schedule)
        enable task: <name> Enable a task and reload the scheduler
        disable task: <name> Disable a task and reload the scheduler
        model               Show current model
        model: <model-id>   Switch model instantly (saved to .env)
        notes               List all note projects with counts
        note: <project> | <idea>  Save an idea to a project
        note: <idea>        Save an idea to 'general' project
        recall: <project>   Retrieve all notes for a project
        recall: <project> | <theme>  Search notes by theme
        search: <query>     Search your memory for a topic
        ingest: <url>       Fetch and store a web page
        ingest pdf: <path>  Extract and store text from a PDF
        <url>               Bare URL — same as ingest:
        exit / quit         Exit (terminal only)

        Anything else is sent to the AI.
        Send a PDF via Telegram to ingest it automatically.

        Model: {config.OPENROUTER_MODEL}
        ─────────────────────────────────────────
    """).strip()


# ---------------------------------------------------------------------------
# Skill / Task file-write extraction
# ---------------------------------------------------------------------------

def _extract_note_directive(response: str) -> tuple:
    """
    Detect [SAVE_NOTE: project]content[/SAVE_NOTE] in an LLM response.
    If found, strips the tag and returns the note for immediate storage.
    Returns (cleaned_response, note_dict | None)
    """
    pattern = re.compile(
        r'\[SAVE_NOTE:\s*([^\]]+)\](.*?)\[/SAVE_NOTE\]',
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(response)
    if match:
        project = match.group(1).strip()
        content = match.group(2).strip()
        cleaned = pattern.sub("", response).strip()
        return cleaned, {"project": project, "content": content}
    return response, None


def _extract_save_directive(response: str) -> tuple:
    """
    Scan the LLM response for a [SAVE_SKILL: name.md] or [SAVE_TASK: name.py]
    directive block. If found, extract the content, strip the block from the
    visible response, and return a pending-write dict.

    The LLM uses this format (defined in IDENTITY.md):
        [SAVE_SKILL: filename.md]
        <skill markdown content>
        [/SAVE_SKILL]

        [SAVE_TASK: filename.py]
        <Python task code>
        [/SAVE_TASK]

    Returns:
        (display_response: str, pending: dict | None)
        pending dict has keys: path, content, type
    """
    for tag, directory, ftype in [
        ("SAVE_SKILL", "skills", "skill"),
        ("SAVE_TASK",  "tasks",  "task"),
    ]:
        pattern = re.compile(
            rf'\[{tag}:\s*([^\]]+)\](.*?)\[/{tag}\]',
            re.DOTALL | re.IGNORECASE,
        )
        match = pattern.search(response)
        if match:
            filename = match.group(1).strip()
            content  = match.group(2).strip()
            path     = PROJECT_DIR / directory / filename

            # Remove the raw tag block from the response shown to the user
            cleaned = pattern.sub("", response).strip()

            # Build a short preview (first 6 lines)
            preview_lines = content.splitlines()[:6]
            preview = "\n".join(preview_lines)
            if len(content.splitlines()) > 6:
                preview += "\n..."

            # Append a confirmation prompt to the cleaned response
            display = (
                f"{cleaned}\n\n"
                f"──────────────────────────────\n"
                f"Ready to save {ftype}: {filename}\n"
                f"──────────────────────────────\n"
                f"{preview}\n"
                f"──────────────────────────────\n"
                f"Reply yes to save, no to cancel."
            )

            pending = {"path": str(path), "content": content, "type": ftype}
            return display, pending

    return response, None


# ---------------------------------------------------------------------------
# Terminal loop
# ---------------------------------------------------------------------------

def _terminal_loop() -> None:
    """Interactive readline loop for terminal use."""
    import config
    print(f"\nMolluskAI ready  •  model: {config.OPENROUTER_MODEL}")
    print("Type 'help' for commands, 'exit' to quit.\n")

    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if text.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        if not text:
            continue

        handle_message(text, lambda r: print(f"\nagent> {r}\n"))


if __name__ == "__main__":
    main()
