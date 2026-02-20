# config.py — Load configuration from .env and provide project-wide constants
#
# This module is imported by all other modules. It reads the .env file once
# at startup and exposes settings as simple module-level variables.

import os
from pathlib import Path

from dotenv import load_dotenv

# Path to the .env file (same directory as this file)
ENV_FILE = Path(__file__).parent / ".env"

# Load the .env file into environment variables
load_dotenv(ENV_FILE)

# --- Required settings ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL   = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

# --- Telegram settings ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Parse comma-separated allowed user IDs into a list of integers
_raw_allowed = os.getenv("TELEGRAM_ALLOWED_USERS", "")
TELEGRAM_ALLOWED_USERS = [
    int(uid.strip())
    for uid in _raw_allowed.split(",")
    if uid.strip().isdigit()
]

# --- Popular models shown in the onboarding dropdown ---
POPULAR_MODELS = [
    "google/gemini-2.0-flash-001",
    "anthropic/claude-3-5-haiku",
    "openai/gpt-4o-mini",
    "meta-llama/llama-3.3-70b-instruct",
    "mistralai/mistral-7b-instruct",
    "deepseek/deepseek-chat",
    "google/gemini-flash-1.5",
    "nousresearch/hermes-3-llama-3.1-70b",
]


def is_configured() -> bool:
    """Return True if the .env file exists and the API key is set."""
    return ENV_FILE.exists() and bool(OPENROUTER_API_KEY)
