# memory.py — Vector memory store
#
# Stores conversation history and long-term memories in SQLite.
# Uses sqlite-vec for fast KNN vector search and fastembed for local embeddings.
#
# Graceful fallbacks:
#   - fastembed unavailable  → full-text search (SQLite FTS5)
#   - sqlite-vec unavailable → numpy cosine similarity over stored BLOBs
#   - numpy unavailable      → full-text search only
#
# Public API:
#   init()                         — create tables, call once at startup
#   store_memory(content, ...)     — embed and store a long-term memory
#   store_conversation(role, text) — append a conversation turn
#   get_recent(n)                  — last n conversation turns
#   search(query, n)               — semantic (or FTS) search
#   ingest_url(url)                — fetch, chunk, embed, and store a web page
#   ingest_pdf(path)               — extract, chunk, embed, and store a PDF

import sqlite3
import struct
from pathlib import Path
from typing import Optional

DB_PATH       = Path(__file__).parent / "data" / "memory.db"
EMBEDDING_DIM = 384  # BAAI/bge-small-en-v1.5 produces 384-dimensional vectors

# ---------------------------------------------------------------------------
# Optional dependency: fastembed
# ---------------------------------------------------------------------------
try:
    from fastembed import TextEmbedding as _TextEmbedding
    _embed_model = _TextEmbedding("BAAI/bge-small-en-v1.5")
    EMBEDDINGS_AVAILABLE = True
    print("[memory] fastembed loaded — using BAAI/bge-small-en-v1.5")
except Exception:
    EMBEDDINGS_AVAILABLE = False
    print("[memory] fastembed not available — falling back to full-text search")

# ---------------------------------------------------------------------------
# Optional dependency: sqlite-vec
# ---------------------------------------------------------------------------
try:
    import sqlite_vec as _sqlite_vec
    SQLITE_VEC_AVAILABLE = True
    print("[memory] sqlite-vec loaded — using KNN vector search")
except Exception:
    SQLITE_VEC_AVAILABLE = False
    print("[memory] sqlite-vec not available — using numpy cosine similarity")

# ---------------------------------------------------------------------------
# Optional dependency: numpy (only needed if sqlite-vec is absent)
# ---------------------------------------------------------------------------
NUMPY_AVAILABLE = False
if EMBEDDINGS_AVAILABLE and not SQLITE_VEC_AVAILABLE:
    try:
        import numpy as _np
        NUMPY_AVAILABLE = True
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    """Open the database and load sqlite-vec extension if available."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if SQLITE_VEC_AVAILABLE:
        conn.enable_load_extension(True)
        _sqlite_vec.load(conn)
        conn.enable_load_extension(False)

    return conn


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init() -> None:
    """
    Create all required tables if they don't already exist.
    Call this once at agent startup.
    """
    conn = _connect()

    # Main memory store — text and metadata
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            content   TEXT    NOT NULL,
            role      TEXT    DEFAULT 'note',
            source    TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # FTS5 full-text search index (used as fallback when embeddings unavailable)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
        USING fts5(content, content='memories', content_rowid='id')
    """)

    # KNN vector table (only created if sqlite-vec is available)
    if SQLITE_VEC_AVAILABLE:
        conn.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_vec
            USING vec0(embedding float[{EMBEDDING_DIM}])
        """)

    # If using numpy fallback, add an embedding BLOB column to the memories table
    if EMBEDDINGS_AVAILABLE and not SQLITE_VEC_AVAILABLE:
        existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(memories)")]
        if "embedding" not in existing_cols:
            conn.execute("ALTER TABLE memories ADD COLUMN embedding BLOB")

    # Conversation history — recent turns fed into every LLM call
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversation (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            role      TEXT    NOT NULL,
            content   TEXT    NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _embed(text: str) -> Optional[list]:
    """Return a float list embedding for text, or None if unavailable."""
    if not EMBEDDINGS_AVAILABLE:
        return None
    result = list(_embed_model.embed([text]))
    return result[0].tolist()


def _pack(vec: list) -> bytes:
    """Serialise a float list to bytes for SQLite storage."""
    return struct.pack(f"{len(vec)}f", *vec)


def _unpack(blob: bytes) -> list:
    """Deserialise bytes back to a float list."""
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def store_memory(content: str, role: str = "note", source: str = None) -> None:
    """
    Store a piece of text as a long-term memory with an embedding.

    content: The text to remember.
    role:    Label for the memory ('note', 'conversation', 'document').
    source:  Optional identifier (e.g. URL or filename).
    """
    vec = _embed(content)
    conn = _connect()

    cursor = conn.execute(
        "INSERT INTO memories (content, role, source) VALUES (?, ?, ?)",
        (content, role, source),
    )
    row_id = cursor.lastrowid

    # Keep FTS index in sync
    conn.execute(
        "INSERT INTO memories_fts(rowid, content) VALUES (?, ?)",
        (row_id, content),
    )

    if vec is not None:
        if SQLITE_VEC_AVAILABLE:
            conn.execute(
                "INSERT INTO memories_vec(rowid, embedding) VALUES (?, ?)",
                (row_id, _pack(vec)),
            )
        elif NUMPY_AVAILABLE:
            conn.execute(
                "UPDATE memories SET embedding = ? WHERE id = ?",
                (_pack(vec), row_id),
            )

    conn.commit()
    conn.close()


def store_conversation(role: str, content: str) -> None:
    """
    Append a single turn to the conversation history.
    role:    'user' or 'assistant'
    content: The message text.
    """
    conn = _connect()
    conn.execute(
        "INSERT INTO conversation (role, content) VALUES (?, ?)",
        (role, content),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def get_recent(n: int = 15) -> list:
    """
    Return the last n conversation turns as a list of dicts.
    Format: [{"role": "user"/"assistant", "content": "..."}, ...]
    Suitable for direct use as the messages list in an LLM call.
    """
    conn = _connect()
    rows = conn.execute(
        "SELECT role, content FROM conversation ORDER BY id DESC LIMIT ?",
        (n,),
    ).fetchall()
    conn.close()
    # Reverse so the oldest turn comes first (correct chronological order for the LLM)
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def search(query: str, n: int = 5) -> list:
    """
    Find the n most relevant memories for a query string.
    Returns a list of dicts with keys: content, role, source, timestamp.

    Search method chosen automatically:
      1. sqlite-vec KNN  — fastest, if sqlite-vec + fastembed are available
      2. numpy cosine    — if fastembed available but sqlite-vec is not
      3. FTS5 full-text  — fallback when embeddings are unavailable
    """
    conn = _connect()
    results = []
    vec = _embed(query)

    if vec is not None and SQLITE_VEC_AVAILABLE:
        # KNN vector search via sqlite-vec
        rows = conn.execute(
            """
            SELECT m.content, m.role, m.source, m.timestamp
            FROM memories m
            INNER JOIN (
                SELECT rowid, distance
                FROM memories_vec
                WHERE embedding MATCH ?
                ORDER BY distance
                LIMIT ?
            ) v ON m.id = v.rowid
            ORDER BY v.distance
            """,
            (_pack(vec), n),
        ).fetchall()
        results = [dict(r) for r in rows]

    elif vec is not None and NUMPY_AVAILABLE:
        # Load all stored embeddings and compute cosine similarity in Python
        rows = conn.execute(
            "SELECT id, content, role, source, timestamp, embedding "
            "FROM memories WHERE embedding IS NOT NULL"
        ).fetchall()
        if rows:
            query_arr = _np.array(vec)
            scored = []
            for row in rows:
                stored_arr = _np.array(_unpack(row["embedding"]))
                denom = _np.linalg.norm(query_arr) * _np.linalg.norm(stored_arr)
                score = float(_np.dot(query_arr, stored_arr) / denom) if denom > 0 else 0.0
                scored.append((score, dict(row)))
            scored.sort(key=lambda x: x[0], reverse=True)
            results = [r for _, r in scored[:n]]
            # Remove internal fields before returning
            for r in results:
                r.pop("embedding", None)
                r.pop("id", None)

    else:
        # FTS5 full-text search fallback
        try:
            rows = conn.execute(
                """
                SELECT m.content, m.role, m.source, m.timestamp
                FROM memories m
                INNER JOIN (
                    SELECT rowid FROM memories_fts WHERE memories_fts MATCH ? LIMIT ?
                ) f ON m.id = f.rowid
                """,
                (query, n),
            ).fetchall()
            results = [dict(r) for r in rows]
        except Exception:
            # FTS5 query syntax errors (e.g. special characters) are silently ignored
            results = []

    conn.close()
    return results


# ---------------------------------------------------------------------------
# Document ingestion
# ---------------------------------------------------------------------------

def _chunk_text(text: str, max_words: int = 400) -> list:
    """Split text into chunks of approximately max_words words."""
    words = text.split()
    return [
        " ".join(words[i : i + max_words])
        for i in range(0, len(words), max_words)
        if words[i : i + max_words]
    ]


def ingest_url(url: str) -> str:
    """
    Fetch a URL, strip HTML, chunk the text, embed each chunk, and store.
    Returns a human-readable confirmation string.
    """
    try:
        import requests as _requests
        from bs4 import BeautifulSoup
    except ImportError:
        return "Error: 'requests' and 'beautifulsoup4' are required. Run: pip install requests beautifulsoup4"

    try:
        resp = _requests.get(url, timeout=15, headers={"User-Agent": "MolluskAI/1.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove noisy elements before extracting text
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
    except Exception as e:
        return f"Error fetching URL: {e}"

    chunks = _chunk_text(text)
    for chunk in chunks:
        store_memory(chunk, role="document", source=url)

    return f"Stored {len(chunks)} chunk(s) from: {url}"


def ingest_pdf(path: str) -> str:
    """
    Extract text from a PDF, chunk, embed, and store.
    Returns a human-readable confirmation string.
    """
    try:
        import fitz  # pymupdf
    except ImportError:
        return "Error: 'pymupdf' is required. Run: pip install pymupdf"

    try:
        doc = fitz.open(path)
        pages_text = [page.get_text() for page in doc]
        doc.close()
        text = " ".join(pages_text)
    except Exception as e:
        return f"Error reading PDF '{path}': {e}"

    source = Path(path).name
    chunks = _chunk_text(text)
    for chunk in chunks:
        store_memory(chunk, role="document", source=source)

    return f"Stored {len(chunks)} chunk(s) from: {source}"
