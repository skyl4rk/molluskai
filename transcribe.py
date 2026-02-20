# transcribe.py — Speech-to-text using faster-whisper
#
# Used by telegram_bot.py to transcribe Telegram voice messages before
# passing them to handle_message() as plain text.
#
# Model is loaded lazily on first use to avoid startup overhead.
# The 'tiny' model (~40MB) is a good default for Raspberry Pi:
#   - Downloads once to ~/.cache/huggingface/hub/ on first use
#   - Runs on CPU with int8 quantisation for efficiency
#
# To use a larger model, change WHISPER_MODEL below:
#   tiny   ~39MB   fastest, less accurate
#   base   ~74MB   good balance
#   small  ~244MB  better quality, slower on Pi

import os

# Suppress CTranslate2 verbose logging
os.environ.setdefault("CT2_VERBOSE", "0")

WHISPER_MODEL = "tiny"

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WhisperModel = None
    WHISPER_AVAILABLE = False

_model = None


def _get_model() -> "WhisperModel":
    """Load the Whisper model on first call, then cache it."""
    global _model
    if _model is None:
        print(f"[transcribe] Loading Whisper '{WHISPER_MODEL}' model (first use may download ~40MB)…")
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        print("[transcribe] Whisper model ready.")
    return _model


def transcribe(audio_path: str) -> str:
    """
    Transcribe an audio file (OGG, WAV, MP3, etc.) to text.
    Returns the transcribed string, or empty string on failure.
    Requires: pip install faster-whisper  and  sudo apt install ffmpeg
    """
    if not WHISPER_AVAILABLE:
        return ""
    try:
        model = _get_model()
        segments, _ = model.transcribe(audio_path, beam_size=1)
        return " ".join(seg.text.strip() for seg in segments).strip()
    except Exception as e:
        print(f"[transcribe] Error transcribing {audio_path}: {e}")
        return ""
