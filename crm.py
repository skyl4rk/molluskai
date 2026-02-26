# crm.py — Personal CRM database layer
#
# Database: data/crm.db (separate from data/memory.db)
# Embeddings: reuses fastembed via memory._embed — no second model loaded on the Pi.
#
# Public API:
#   init()                              — create tables, call once at agent startup
#   add_contact(name, email, ...)       — upsert contact, returns contact_id
#   get_contact(email, contact_id, name) — lookup, returns dict or None
#   update_relationship_score(id)       — recalculate score, returns float
#   add_interaction(id, type, summary, event_date, source)
#   add_follow_up(id, due_date, note)   — returns follow_up_id
#   get_pending_follow_ups(days_ahead)  — list of dicts
#   search_contacts(query, n)           — FTS5 or LIKE fallback
#   add_context(id, content, source)    — store embedded context chunk
#   get_contact_context(id, query, n)   — semantic or recency retrieval
#   get_or_create_proposal(email, name) — upsert pending_proposals
#   approve_proposal(email)             — convert to contact, returns contact_id
#   reject_proposal(email)              — add to skip_patterns
#   is_skipped(email)                   — check skip_patterns + config.CRM_SKIP_DOMAINS
#   get_stats()                         — summary counts dict

import sqlite3
import struct
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import config

DB_PATH = Path(__file__).parent / "data" / "crm.db"

# ---------------------------------------------------------------------------
# Borrow embedding helpers from memory.py — avoids loading a second model
# ---------------------------------------------------------------------------
try:
    from memory import _embed, _pack, _unpack, EMBEDDINGS_AVAILABLE
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    def _embed(text):  return None
    def _pack(vec):    return b""
    def _unpack(blob): return []

try:
    import numpy as _np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    """Open crm.db with WAL mode. Returns connection with row_factory set."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init() -> None:
    """Create all CRM tables if they don't exist. Call once at agent startup."""
    conn = _connect()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT    NOT NULL,
            email               TEXT    UNIQUE,
            phone               TEXT,
            company             TEXT,
            role                TEXT,
            notes               TEXT,
            relationship_score  REAL    DEFAULT 0.0,
            last_contact_date   DATE,
            created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id    INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
            type          TEXT    NOT NULL,
            summary       TEXT,
            event_date    DATETIME,
            source        TEXT,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS follow_ups (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id    INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
            due_date      DATE    NOT NULL,
            note          TEXT,
            completed     INTEGER DEFAULT 0,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS contact_context (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id    INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
            content       TEXT    NOT NULL,
            source        TEXT,
            embedding     BLOB,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS contact_summaries (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id    INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
            summary       TEXT    NOT NULL,
            generated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS skip_patterns (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern       TEXT    NOT NULL UNIQUE,
            pattern_type  TEXT    DEFAULT 'address',
            reason        TEXT    DEFAULT 'user_rejected',
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending_proposals (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email         TEXT    NOT NULL UNIQUE,
            name          TEXT,
            company       TEXT,
            seen_count    INTEGER DEFAULT 1,
            first_seen    DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_seen     DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # FTS5 index for fast contact name/email/company search
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS contacts_fts
        USING fts5(name, email, company, notes, content='contacts', content_rowid='id')
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Contact operations
# ---------------------------------------------------------------------------

def add_contact(
    name: str,
    email: str = None,
    phone: str = None,
    company: str = None,
    role: str = None,
    notes: str = None,
) -> int:
    """
    Upsert a contact by email. If email matches an existing contact,
    updates any non-null fields. Returns contact_id.
    """
    conn = _connect()
    now = datetime.now().isoformat()

    if email:
        email = email.lower().strip()
        existing = conn.execute(
            "SELECT id FROM contacts WHERE email = ?", (email,)
        ).fetchone()
    else:
        existing = None

    if existing:
        contact_id = existing["id"]
        # Update non-null fields
        updates = {"updated_at": now}
        if name:     updates["name"]    = name
        if phone:    updates["phone"]   = phone
        if company:  updates["company"] = company
        if role:     updates["role"]    = role
        if notes:    updates["notes"]   = notes
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE contacts SET {set_clause} WHERE id = ?",
            (*updates.values(), contact_id),
        )
    else:
        cursor = conn.execute(
            "INSERT INTO contacts (name, email, phone, company, role, notes, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, email, phone, company, role, notes, now),
        )
        contact_id = cursor.lastrowid
        # Rebuild FTS index entry
        conn.execute(
            "INSERT INTO contacts_fts(rowid, name, email, company, notes) VALUES (?, ?, ?, ?, ?)",
            (contact_id, name or "", email or "", company or "", notes or ""),
        )

    conn.commit()
    conn.close()
    return contact_id


def get_contact(
    email: str = None,
    contact_id: int = None,
    name: str = None,
) -> Optional[dict]:
    """
    Look up a contact. Priority: contact_id > email > name (FTS).
    Returns a dict of all columns or None if not found.
    """
    conn = _connect()
    row = None

    if contact_id is not None:
        row = conn.execute(
            "SELECT * FROM contacts WHERE id = ?", (contact_id,)
        ).fetchone()
    elif email:
        row = conn.execute(
            "SELECT * FROM contacts WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
    elif name:
        try:
            fts_row = conn.execute(
                "SELECT rowid FROM contacts_fts WHERE contacts_fts MATCH ? LIMIT 1",
                (name,),
            ).fetchone()
            if fts_row:
                row = conn.execute(
                    "SELECT * FROM contacts WHERE id = ?", (fts_row["rowid"],)
                ).fetchone()
        except Exception:
            row = conn.execute(
                "SELECT * FROM contacts WHERE name LIKE ? LIMIT 1",
                (f"%{name}%",),
            ).fetchone()

    conn.close()
    return dict(row) if row else None


def update_relationship_score(contact_id: int) -> float:
    """
    Recalculate and persist relationship score for one contact.

    Score formula (0–100):
      recency_score   = max(0, 100 - days_since_last_contact * 2)
      frequency_score = min(100, interactions_last_90_days * 10)
      score = recency_score * 0.6 + frequency_score * 0.4
    """
    conn = _connect()
    now = datetime.now()

    # Most recent interaction
    last_row = conn.execute(
        "SELECT MAX(event_date) as last_dt FROM interactions WHERE contact_id = ?",
        (contact_id,),
    ).fetchone()

    last_dt_str = last_row["last_dt"] if last_row else None
    if last_dt_str:
        try:
            last_dt = datetime.fromisoformat(str(last_dt_str)[:19])
            days_since = (now - last_dt).days
        except Exception:
            days_since = 999
    else:
        days_since = 999

    # Interactions in last 90 days
    cutoff_90 = (now - timedelta(days=90)).isoformat()
    count_row = conn.execute(
        "SELECT COUNT(*) as cnt FROM interactions WHERE contact_id = ? AND event_date >= ?",
        (contact_id, cutoff_90),
    ).fetchone()
    recent_count = count_row["cnt"] if count_row else 0

    recency_score   = max(0.0, 100.0 - days_since * 2)
    frequency_score = min(100.0, recent_count * 10.0)
    score = round(recency_score * 0.6 + frequency_score * 0.4, 2)

    last_contact_date = last_dt_str[:10] if last_dt_str else None
    conn.execute(
        "UPDATE contacts SET relationship_score = ?, last_contact_date = ?, updated_at = ? "
        "WHERE id = ?",
        (score, last_contact_date, now.isoformat(), contact_id),
    )
    conn.commit()
    conn.close()
    return score


# ---------------------------------------------------------------------------
# Interactions and follow-ups
# ---------------------------------------------------------------------------

def add_interaction(
    contact_id: int,
    interaction_type: str,
    summary: str = None,
    event_date: datetime = None,
    source: str = None,
) -> int:
    """
    Insert an interaction and update the contact's relationship score.
    interaction_type: 'email_in', 'email_out', 'calendar_event', 'manual', 'draft_sent'
    source:           'imap_scan', 'caldav_scan', 'manual', 'email_draft'
    Returns interaction_id.
    """
    conn = _connect()
    event_dt = (event_date or datetime.now()).isoformat()
    cursor = conn.execute(
        "INSERT INTO interactions (contact_id, type, summary, event_date, source) "
        "VALUES (?, ?, ?, ?, ?)",
        (contact_id, interaction_type, summary, event_dt, source),
    )
    interaction_id = cursor.lastrowid
    conn.commit()
    conn.close()
    update_relationship_score(contact_id)
    return interaction_id


def add_follow_up(contact_id: int, due_date, note: str = None) -> int:
    """
    Schedule a follow-up for a contact.
    due_date: date object or 'YYYY-MM-DD' string.
    Returns follow_up_id.
    """
    conn = _connect()
    due_str = str(due_date)[:10]
    cursor = conn.execute(
        "INSERT INTO follow_ups (contact_id, due_date, note) VALUES (?, ?, ?)",
        (contact_id, due_str, note),
    )
    follow_up_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return follow_up_id


def get_pending_follow_ups(days_ahead: int = 7) -> list:
    """
    Return follow-ups due within days_ahead days that are not yet completed.
    Returns list of dicts: {follow_up_id, contact_id, contact_name, email, due_date, note}
    """
    cutoff = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    conn = _connect()
    rows = conn.execute(
        """
        SELECT f.id as follow_up_id, f.contact_id, f.due_date, f.note,
               c.name as contact_name, c.email
        FROM follow_ups f
        JOIN contacts c ON c.id = f.contact_id
        WHERE f.completed = 0 AND f.due_date <= ?
        ORDER BY f.due_date ASC
        """,
        (cutoff,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Contact context (semantic memory per contact)
# ---------------------------------------------------------------------------

def add_context(contact_id: int, content: str, source: str = None) -> None:
    """Store a text chunk about a contact, with embedding if available."""
    vec = _embed(content)
    blob = _pack(vec) if vec else None
    conn = _connect()
    conn.execute(
        "INSERT INTO contact_context (contact_id, content, source, embedding) VALUES (?, ?, ?, ?)",
        (contact_id, content, source, blob),
    )
    conn.commit()
    conn.close()


def get_contact_context(
    contact_id: int,
    query: str = None,
    n: int = 5,
) -> list:
    """
    Retrieve top-N context chunks for a contact.
    If query provided and numpy available: cosine similarity ranking.
    Otherwise: most recent N chunks.
    Returns list of dicts: {content, source, created_at}
    """
    conn = _connect()

    if query and EMBEDDINGS_AVAILABLE and NUMPY_AVAILABLE:
        query_vec = _embed(query)
        if query_vec:
            rows = conn.execute(
                "SELECT content, source, created_at, embedding FROM contact_context "
                "WHERE contact_id = ? AND embedding IS NOT NULL",
                (contact_id,),
            ).fetchall()
            if rows:
                q_arr = _np.array(query_vec)
                scored = []
                for row in rows:
                    s_arr = _np.array(_unpack(row["embedding"]))
                    denom = _np.linalg.norm(q_arr) * _np.linalg.norm(s_arr)
                    score = float(_np.dot(q_arr, s_arr) / denom) if denom > 0 else 0.0
                    scored.append((score, {"content": row["content"], "source": row["source"],
                                           "created_at": row["created_at"]}))
                scored.sort(key=lambda x: x[0], reverse=True)
                conn.close()
                return [r for _, r in scored[:n]]

    # Fallback: most recent chunks
    rows = conn.execute(
        "SELECT content, source, created_at FROM contact_context "
        "WHERE contact_id = ? ORDER BY created_at DESC LIMIT ?",
        (contact_id, n),
    ).fetchall()
    conn.close()
    return [{"content": r["content"], "source": r["source"], "created_at": r["created_at"]}
            for r in rows]


# ---------------------------------------------------------------------------
# Contact search
# ---------------------------------------------------------------------------

def search_contacts(query: str, n: int = 10) -> list:
    """
    Search contacts by name, email, company, or notes.
    Uses FTS5 with LIKE fallback. Returns list of contact dicts.
    """
    conn = _connect()
    results = []

    try:
        fts_rows = conn.execute(
            "SELECT rowid FROM contacts_fts WHERE contacts_fts MATCH ? LIMIT ?",
            (query, n),
        ).fetchall()
        if fts_rows:
            ids = tuple(r["rowid"] for r in fts_rows)
            placeholders = ",".join("?" * len(ids))
            rows = conn.execute(
                f"SELECT * FROM contacts WHERE id IN ({placeholders})", ids
            ).fetchall()
            results = [dict(r) for r in rows]
    except Exception:
        pass

    if not results:
        rows = conn.execute(
            "SELECT * FROM contacts WHERE name LIKE ? OR email LIKE ? OR company LIKE ? LIMIT ?",
            (f"%{query}%", f"%{query}%", f"%{query}%", n),
        ).fetchall()
        results = [dict(r) for r in rows]

    conn.close()
    return results


# ---------------------------------------------------------------------------
# Proposal management
# ---------------------------------------------------------------------------

def get_or_create_proposal(
    email: str,
    name: str = None,
    company: str = None,
) -> dict:
    """
    Upsert a pending_proposals row. Increments seen_count and updates last_seen.
    Returns the proposal row as a dict.
    """
    email = email.lower().strip()
    conn = _connect()
    now = datetime.now().isoformat()

    existing = conn.execute(
        "SELECT * FROM pending_proposals WHERE email = ?", (email,)
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE pending_proposals SET seen_count = seen_count + 1, last_seen = ? WHERE email = ?",
            (now, email),
        )
        row = conn.execute(
            "SELECT * FROM pending_proposals WHERE email = ?", (email,)
        ).fetchone()
    else:
        conn.execute(
            "INSERT INTO pending_proposals (email, name, company) VALUES (?, ?, ?)",
            (email, name, company),
        )
        row = conn.execute(
            "SELECT * FROM pending_proposals WHERE email = ?", (email,)
        ).fetchone()

    conn.commit()
    conn.close()
    return dict(row)


def approve_proposal(email: str) -> int:
    """
    Convert a pending proposal to a contact.
    Deletes from pending_proposals. Returns new contact_id.
    """
    email = email.lower().strip()
    conn = _connect()
    proposal = conn.execute(
        "SELECT * FROM pending_proposals WHERE email = ?", (email,)
    ).fetchone()
    conn.close()

    name = (proposal["name"] if proposal else None) or email.split("@")[0]
    company = proposal["company"] if proposal else None

    contact_id = add_contact(name=name, email=email, company=company)

    conn = _connect()
    conn.execute("DELETE FROM pending_proposals WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    return contact_id


def reject_proposal(email: str) -> None:
    """Add email to skip_patterns and remove from pending_proposals."""
    email = email.lower().strip()
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO skip_patterns (pattern, pattern_type, reason) VALUES (?, ?, ?)",
            (email, "address", "user_rejected"),
        )
    except Exception:
        pass
    conn.execute("DELETE FROM pending_proposals WHERE email = ?", (email,))
    conn.commit()
    conn.close()


def is_skipped(email: str) -> bool:
    """
    Return True if email matches a skip_patterns row or config.CRM_SKIP_DOMAINS.
    Checks full address match and @domain suffix match.
    """
    email = email.lower().strip()
    domain = email.split("@")[-1] if "@" in email else ""

    # Check config-level domain keywords (no DB query needed)
    for keyword in config.CRM_SKIP_DOMAINS:
        if keyword in email:
            return True

    conn = _connect()
    row = conn.execute(
        "SELECT id FROM skip_patterns WHERE pattern = ? OR pattern = ? LIMIT 1",
        (email, f"@{domain}"),
    ).fetchone()
    conn.close()
    return row is not None


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def get_stats() -> dict:
    """Return summary counts for the daily report."""
    conn = _connect()
    today = datetime.now().strftime("%Y-%m-%d")

    total_contacts = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    interactions_today = conn.execute(
        "SELECT COUNT(*) FROM interactions WHERE date(event_date) = ?", (today,)
    ).fetchone()[0]
    pending_follow_ups = conn.execute(
        "SELECT COUNT(*) FROM follow_ups WHERE completed = 0 AND due_date <= ?", (today,)
    ).fetchone()[0]
    pending_proposals = conn.execute(
        "SELECT COUNT(*) FROM pending_proposals"
    ).fetchone()[0]

    conn.close()
    return {
        "total_contacts":      total_contacts,
        "interactions_today":  interactions_today,
        "pending_follow_ups":  pending_follow_ups,
        "pending_proposals":   pending_proposals,
    }
