# telegram_bot.py — Telegram polling gateway
#
# Runs python-telegram-bot in a background daemon thread using asyncio.
# Handles:
#   - Text messages  → routed to agent.handle_message()
#   - Voice messages → transcribed via faster-whisper, then routed as text
#   - PDF documents  → downloaded, then ingested via memory.ingest_pdf()
#
# Security: only TELEGRAM_ALLOWED_USERS listed in .env are accepted.
# All other users receive a polite refusal.
#
# python-telegram-bot v20+ is async. It runs in its own event loop
# inside a dedicated daemon thread, so it doesn't block the terminal.

import asyncio
import logging
import threading
from pathlib import Path

import config

# Suppress httpx INFO logs — they print the full bot token URL on every poll.
logging.getLogger("httpx").setLevel(logging.WARNING)

DENIED_MESSAGE = (
    "Sorry, I'm a private assistant. "
    "This bot only responds to authorised users."
)
DATA_DIR = Path(__file__).parent / "data"


def start(message_handler) -> None:
    """
    Start the Telegram bot in a background daemon thread.

    message_handler: callable(text: str, reply_fn: callable) → None
                     This is agent.handle_message.
    """
    if not config.TELEGRAM_TOKEN:
        print("[telegram] No TELEGRAM_TOKEN set — Telegram gateway disabled.")
        return

    if not config.TELEGRAM_ALLOWED_USERS:
        print("[telegram] WARNING: TELEGRAM_ALLOWED_USERS is empty — any Telegram user")
        print("[telegram]          can talk to this bot. Add your user ID to .env for security.")
        print("[telegram]          Find your ID by messaging @userinfobot on Telegram.")

    thread = threading.Thread(
        target=_run_bot,
        args=(config.TELEGRAM_TOKEN, message_handler),
        daemon=True,
        name="telegram-bot",
    )
    thread.start()
    print("[telegram] Bot starting (polling)…")


def _run_bot(token: str, message_handler) -> None:
    """Run the async Telegram bot in a dedicated event loop."""
    try:
        from telegram import Update
        from telegram.ext import (
            ApplicationBuilder,
            ContextTypes,
            MessageHandler,
            filters,
        )
    except ImportError:
        print(
            "[telegram] python-telegram-bot is not installed.\n"
            "           Run: pip install python-telegram-bot"
        )
        return

    async def _check_user(update) -> bool:
        """Return True if this user is in the allowed list (or no list is set)."""
        if not config.TELEGRAM_ALLOWED_USERS:
            # No whitelist configured — allow everyone (not recommended)
            return True
        return update.effective_user.id in config.TELEGRAM_ALLOWED_USERS

    async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle plain text messages."""
        if not await _check_user(update):
            await update.message.reply_text(DENIED_MESSAGE)
            return

        text = (update.message.text or "").strip()
        if not text:
            return

        replies = []
        message_handler(text, lambda r: replies.append(r))

        for reply in replies:
            for chunk in _split(reply):
                await update.message.reply_text(chunk)

    async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle voice messages — transcribe and pass to handle_message()."""
        if not await _check_user(update):
            await update.message.reply_text(DENIED_MESSAGE)
            return

        import transcribe
        if not transcribe.WHISPER_AVAILABLE:
            await update.message.reply_text(
                "Voice messages require faster-whisper and ffmpeg.\n"
                "Run:\n"
                "  sudo apt install ffmpeg\n"
                "  pip install faster-whisper"
            )
            return

        await update.message.reply_text("Transcribing…")

        voice = update.message.voice
        DATA_DIR.mkdir(exist_ok=True)
        ogg_path = DATA_DIR / f"voice_{voice.file_id}.ogg"
        tg_file = await context.bot.get_file(voice.file_id)
        await tg_file.download_to_drive(str(ogg_path))

        text = transcribe.transcribe(str(ogg_path))
        ogg_path.unlink(missing_ok=True)  # clean up after transcription

        if not text:
            await update.message.reply_text("Sorry, I couldn't understand the audio.")
            return

        await update.message.reply_text(f"_(Heard: {text})_", parse_mode="Markdown")

        replies = []
        message_handler(text, lambda r: replies.append(r))
        for reply in replies:
            for chunk in _split(reply):
                await update.message.reply_text(chunk)

    async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle PDF file uploads — download and ingest them."""
        if not await _check_user(update):
            await update.message.reply_text(DENIED_MESSAGE)
            return

        doc = update.message.document
        if not doc or not doc.file_name.lower().endswith(".pdf"):
            await update.message.reply_text(
                "Only PDF files are supported. Send a .pdf file to ingest it."
            )
            return

        await update.message.reply_text(f"Downloading {doc.file_name}…")

        DATA_DIR.mkdir(exist_ok=True)
        save_path = DATA_DIR / doc.file_name
        tg_file = await context.bot.get_file(doc.file_id)
        await tg_file.download_to_drive(str(save_path))

        # Use the internal ingest_pdf command so handle_message can route it
        replies = []
        message_handler(f"ingest_pdf:{save_path}", lambda r: replies.append(r))

        for reply in replies:
            await update.message.reply_text(reply)

    async def run():
        app = ApplicationBuilder().token(token).build()
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
        app.add_handler(MessageHandler(filters.VOICE, on_voice))
        app.add_handler(MessageHandler(filters.Document.ALL, on_document))
        # Use async context manager instead of run_polling() to avoid
        # installing OS signal handlers, which only work in the main thread.
        async with app:
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            # Wait indefinitely — this thread is a daemon and will be
            # killed automatically when the main process exits.
            await asyncio.Event().wait()

    # Create a dedicated event loop for this thread.
    # Do NOT use asyncio.run() — it also tries to install signal handlers.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run())
    finally:
        loop.close()


def _split(text: str, max_len: int = 4000) -> list:
    """
    Split a message into chunks that fit within Telegram's 4096-char limit.
    Tries to split at newlines to avoid cutting words.
    """
    if len(text) <= max_len:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # Try to break at the last newline before max_len
        cut = text.rfind("\n", 0, max_len)
        if cut == -1:
            cut = max_len
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")

    return chunks
