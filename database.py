"""
Wissens-SRS Database Layer
SQLite mit allen CRUD-Operationen für Karten, Erklärungen und Review-Log.
"""
import sqlite3
import os
from datetime import date, datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "wissens.db")

def get_db():
    """Verbindung mit row_factory für Dict-Zugriff."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    """Tabellen erstellen (idempotent)."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            explanation TEXT NOT NULL,
            level TEXT NOT NULL CHECK(level IN ('easy','abitur','professor')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            -- SRS Felder (SM-2)
            ease_factor REAL DEFAULT 2.5,
            interval_days INTEGER DEFAULT 0,
            repetitions INTEGER DEFAULT 0,
            next_review DATE,
            last_reviewed DATE,
            -- Metadaten
            review_count INTEGER DEFAULT 0,
            avg_rating REAL DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS explanations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            topic_hash TEXT NOT NULL,
            level TEXT NOT NULL CHECK(level IN ('easy','abitur','professor')),
            explanation TEXT NOT NULL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(topic_hash, level)
        );
        
        CREATE TABLE IF NOT EXISTS review_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
            rating INTEGER NOT NULL CHECK(rating BETWEEN 0 AND 5),
            reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_cards_next_review ON cards(next_review);
        CREATE INDEX IF NOT EXISTS idx_cards_level ON cards(level);
        CREATE INDEX IF NOT EXISTS idx_explanations_hash ON explanations(topic_hash);
        CREATE INDEX IF NOT EXISTS idx_review_log_card ON review_log(card_id);
    """)
    conn.commit()
    conn.close()

# ── Cards CRUD ──────────────────────────────────────────────────

def create_card(topic, explanation, level):
    """Neue SRS-Karte anlegen. Setzt next_review auf heute (sofort fällig)."""
    conn = get_db()
    today = date.today().isoformat()
    cur = conn.execute(
        "INSERT INTO cards (topic, explanation, level, next_review) VALUES (?, ?, ?, ?)",
        (topic, explanation, level, today)
    )
    card_id = cur.lastrowid
    conn.commit()
    conn.close()
    return get_card(card_id)

def get_card(card_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_cards():
    conn = get_db()
    rows = conn.execute("SELECT * FROM cards ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_due_cards():
    """Alle Karten, deren next_review <= heute."""
    conn = get_db()
    today = date.today().isoformat()
    rows = conn.execute(
        "SELECT * FROM cards WHERE next_review <= ? ORDER BY next_review ASC",
        (today,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_card(card_id, **kwargs):
    """SRS-Felder einer Karte aktualisieren."""
    allowed = {'ease_factor', 'interval_days', 'repetitions', 'next_review',
               'last_reviewed', 'review_count', 'avg_rating'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return get_card(card_id)
    
    conn = get_db()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [card_id]
    conn.execute(f"UPDATE cards SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return get_card(card_id)

def delete_card(card_id):
    conn = get_db()
    conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()

# ── Explanations CRUD ───────────────────────────────────────────

def save_explanations(topic, explanations_dict):
    """explanations_dict: {'easy': '...', 'abitur': '...', 'professor': '...'}"""
    import hashlib
    topic_hash = hashlib.md5(topic.strip().lower().encode()).hexdigest()[:12]
    conn = get_db()
    for level, text in explanations_dict.items():
        conn.execute(
            "INSERT OR REPLACE INTO explanations (topic, topic_hash, level, explanation) VALUES (?, ?, ?, ?)",
            (topic, topic_hash, level, text)
        )
    conn.commit()
    conn.close()

def get_explanations(topic):
    """Gespeicherte Erklärungen für ein Topic abrufen."""
    import hashlib
    topic_hash = hashlib.md5(topic.strip().lower().encode()).hexdigest()[:12]
    conn = get_db()
    rows = conn.execute(
        "SELECT level, explanation FROM explanations WHERE topic_hash = ?", (topic_hash,)
    ).fetchall()
    conn.close()
    return {r['level']: r['explanation'] for r in rows}

# ── Review Log ──────────────────────────────────────────────────

def add_review(card_id, rating):
    conn = get_db()
    conn.execute(
        "INSERT INTO review_log (card_id, rating) VALUES (?, ?)",
        (card_id, rating)
    )
    conn.commit()
    conn.close()

# ── Statistics ──────────────────────────────────────────────────

def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) as n FROM cards").fetchone()['n']
    today = date.today().isoformat()
    due = conn.execute(
        "SELECT COUNT(*) as n FROM cards WHERE next_review <= ?", (today,)
    ).fetchone()['n']
    avg = conn.execute("SELECT AVG(avg_rating) as a FROM cards WHERE review_count > 0").fetchone()['a']
    conn.close()
    return {
        "total": total,
        "due": due,
        "avg_rating": round(avg, 2) if avg else 0
    }
