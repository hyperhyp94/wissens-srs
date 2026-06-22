"""
Wissens-SRS Database Layer
SQLite mit allen CRUD-Operationen für Karten, Erklärungen, Tags, Sprachkarten und Review-Log.
"""
import sqlite3
import os
from datetime import date

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "wissens.db")

def get_db():
    """Verbindung mit row_factory für Dict-Zugriff."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Migration Helpers ────────────────────────────────────────────

def _migrate_cards_table(conn):
    """Rebuild cards: old level names (easy/gruendlich/experte) → new (kurz/kompakt/ausfuehrlich), add title."""
    conn.execute("PRAGMA foreign_keys=OFF")

    old_cols = [r['name'] for r in conn.execute("PRAGMA table_info(cards)").fetchall()]
    has_title = 'title' in old_cols
    title_expr = "COALESCE(NULLIF(title,''), topic)" if has_title else "topic"

    conn.execute("""CREATE TABLE cards_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        title TEXT,
        explanation TEXT NOT NULL,
        level TEXT NOT NULL CHECK(level IN ('kurz','kompakt','ausfuehrlich')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ease_factor REAL DEFAULT 2.5,
        interval_days INTEGER DEFAULT 0,
        repetitions INTEGER DEFAULT 0,
        next_review DATE,
        last_reviewed DATE,
        review_count INTEGER DEFAULT 0,
        avg_rating REAL DEFAULT 0
    )""")

    conn.execute(f"""INSERT INTO cards_new
        SELECT id, topic, {title_expr} AS title, explanation,
            CASE level
                WHEN 'easy'       THEN 'kurz'
                WHEN 'gruendlich' THEN 'kompakt'
                WHEN 'experte'    THEN 'ausfuehrlich'
                ELSE 'kurz'
            END AS level,
            created_at, ease_factor, interval_days, repetitions,
            next_review, last_reviewed, review_count, avg_rating
        FROM cards""")

    conn.execute("DROP TABLE cards")
    conn.execute("ALTER TABLE cards_new RENAME TO cards")
    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")


def _migrate_explanations_table(conn):
    """Drop and recreate explanations with new level constraint (cache is regeneratable)."""
    conn.execute("DROP TABLE IF EXISTS explanations")
    conn.execute("""CREATE TABLE explanations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        topic_hash TEXT NOT NULL,
        level TEXT NOT NULL CHECK(level IN ('kurz','kompakt','ausfuehrlich')),
        explanation TEXT NOT NULL,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(topic_hash, level)
    )""")
    conn.commit()


# ── Init ─────────────────────────────────────────────────────────

def init_db():
    """Tabellen erstellen und Migrationen durchführen (idempotent)."""
    conn = get_db()

    # ── Tabellen ohne Migrations-Abhängigkeit ──────────────────
    conn.execute("""CREATE TABLE IF NOT EXISTS review_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
        rating INTEGER NOT NULL CHECK(rating BETWEEN 0 AND 5),
        reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # T0.4: Tags
    conn.execute("""CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS card_tags (
        card_id INTEGER REFERENCES cards(id) ON DELETE CASCADE,
        tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
        PRIMARY KEY(card_id, tag_id)
    )""")

    # T0.5: Sprachkarten
    conn.execute("""CREATE TABLE IF NOT EXISTS language_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_text TEXT NOT NULL,
        target_text TEXT NOT NULL,
        source_lang TEXT DEFAULT 'de',
        target_lang TEXT DEFAULT 'en',
        level TEXT NOT NULL CHECK(level IN ('einfach','mittel','fortgeschritten')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ease_factor REAL DEFAULT 2.5,
        interval_days INTEGER DEFAULT 0,
        repetitions INTEGER DEFAULT 0,
        next_review DATE,
        last_reviewed DATE,
        review_count INTEGER DEFAULT 0,
        avg_rating REAL DEFAULT 0
    )""")
    conn.commit()

    # ── T0.2: cards table (mit Migration) ─────────────────────
    cards_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='cards'"
    ).fetchone()

    if not cards_exists:
        conn.execute("""CREATE TABLE cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            title TEXT,
            explanation TEXT NOT NULL,
            level TEXT NOT NULL CHECK(level IN ('kurz','kompakt','ausfuehrlich')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ease_factor REAL DEFAULT 2.5,
            interval_days INTEGER DEFAULT 0,
            repetitions INTEGER DEFAULT 0,
            next_review DATE,
            last_reviewed DATE,
            review_count INTEGER DEFAULT 0,
            avg_rating REAL DEFAULT 0
        )""")
        conn.commit()
    else:
        schema = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='cards'"
        ).fetchone()['sql']

        if "'easy'" in schema:
            # T0.2: Rebuild mit Level-Mapping
            _migrate_cards_table(conn)
        else:
            # T0.1: title Spalte ergänzen falls fehlend
            cols = [r['name'] for r in conn.execute("PRAGMA table_info(cards)").fetchall()]
            if 'title' not in cols:
                conn.execute("ALTER TABLE cards ADD COLUMN title TEXT")
                conn.commit()

    # ── T0.3: explanations table (mit Migration) ──────────────
    expl_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='explanations'"
    ).fetchone()

    if not expl_exists:
        conn.execute("""CREATE TABLE explanations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            topic_hash TEXT NOT NULL,
            level TEXT NOT NULL CHECK(level IN ('kurz','kompakt','ausfuehrlich')),
            explanation TEXT NOT NULL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(topic_hash, level)
        )""")
        conn.commit()
    else:
        schema = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='explanations'"
        ).fetchone()['sql']
        if "'easy'" in schema:
            _migrate_explanations_table(conn)

    # ── Indizes ────────────────────────────────────────────────
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_cards_next_review    ON cards(next_review);
        CREATE INDEX IF NOT EXISTS idx_cards_level          ON cards(level);
        CREATE INDEX IF NOT EXISTS idx_explanations_hash    ON explanations(topic_hash);
        CREATE INDEX IF NOT EXISTS idx_review_log_card      ON review_log(card_id);
        CREATE INDEX IF NOT EXISTS idx_card_tags_card       ON card_tags(card_id);
        CREATE INDEX IF NOT EXISTS idx_card_tags_tag        ON card_tags(tag_id);
        CREATE INDEX IF NOT EXISTS idx_language_next_review ON language_cards(next_review);
    """)

    conn.commit()
    conn.close()


# ── Cards CRUD ───────────────────────────────────────────────────

def create_card(topic, explanation, level, title=None):
    """Neue SRS-Karte anlegen. next_review auf heute (sofort fällig)."""
    if title is None:
        title = topic
    conn = get_db()
    today = date.today().isoformat()
    cur = conn.execute(
        "INSERT INTO cards (topic, title, explanation, level, next_review) VALUES (?, ?, ?, ?, ?)",
        (topic, title, explanation, level, today)
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
    """Alle Karten inkl. Tags."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM cards ORDER BY created_at DESC").fetchall()
    cards = [dict(r) for r in rows]
    for card in cards:
        tag_rows = conn.execute("""
            SELECT t.id, t.name FROM tags t
            JOIN card_tags ct ON ct.tag_id = t.id
            WHERE ct.card_id = ?
            ORDER BY t.name
        """, (card['id'],)).fetchall()
        card['tags'] = [dict(t) for t in tag_rows]
    conn.close()
    return cards

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


# ── Tags CRUD ────────────────────────────────────────────────────

def get_all_tags():
    """Alle Tags mit Kartenanzahl."""
    conn = get_db()
    rows = conn.execute("""
        SELECT t.id, t.name, COUNT(ct.card_id) AS card_count
        FROM tags t
        LEFT JOIN card_tags ct ON ct.tag_id = t.id
        GROUP BY t.id, t.name
        ORDER BY t.name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_tag_to_card(card_id, tag_name):
    """Tag anlegen (falls nötig) und Karte zuweisen."""
    tag_name = tag_name.strip().lower()
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
    tag_row = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,)).fetchone()
    tag_id = tag_row['id']
    conn.execute("INSERT OR IGNORE INTO card_tags (card_id, tag_id) VALUES (?, ?)", (card_id, tag_id))
    conn.commit()
    conn.close()
    return {'id': tag_id, 'name': tag_name}

def remove_tag_from_card(card_id, tag_id):
    conn = get_db()
    conn.execute("DELETE FROM card_tags WHERE card_id = ? AND tag_id = ?", (card_id, tag_id))
    conn.commit()
    conn.close()

def get_card_tags(card_id):
    """Tags für eine Karte."""
    conn = get_db()
    rows = conn.execute("""
        SELECT t.id, t.name FROM tags t
        JOIN card_tags ct ON ct.tag_id = t.id
        WHERE ct.card_id = ?
        ORDER BY t.name
    """, (card_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Explanations CRUD ────────────────────────────────────────────

def save_explanations(topic, explanations_dict):
    """explanations_dict: {'kurz': '...', 'kompakt': '...', 'ausfuehrlich': '...'}"""
    import hashlib
    topic_hash = hashlib.md5(topic.strip().lower().encode()).hexdigest()[:12]
    conn = get_db()
    for level, text in explanations_dict.items():
        if text:
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


# ── Review Log ───────────────────────────────────────────────────

def add_review(card_id, rating):
    conn = get_db()
    conn.execute(
        "INSERT INTO review_log (card_id, rating) VALUES (?, ?)",
        (card_id, rating)
    )
    conn.commit()
    conn.close()


# ── Language Cards CRUD ──────────────────────────────────────────

def create_language_card(source_text, target_text, source_lang, target_lang, level):
    conn = get_db()
    today = date.today().isoformat()
    cur = conn.execute(
        """INSERT INTO language_cards
           (source_text, target_text, source_lang, target_lang, level, next_review)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (source_text, target_text, source_lang, target_lang, level, today)
    )
    card_id = cur.lastrowid
    conn.commit()
    conn.close()
    return get_language_card(card_id)

def get_language_card(card_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM language_cards WHERE id = ?", (card_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_language_cards():
    conn = get_db()
    rows = conn.execute("SELECT * FROM language_cards ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_due_language_cards():
    conn = get_db()
    today = date.today().isoformat()
    rows = conn.execute(
        "SELECT * FROM language_cards WHERE next_review <= ? ORDER BY next_review ASC",
        (today,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_language_card(card_id, **kwargs):
    allowed = {'ease_factor', 'interval_days', 'repetitions', 'next_review',
               'last_reviewed', 'review_count', 'avg_rating'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return get_language_card(card_id)
    conn = get_db()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [card_id]
    conn.execute(f"UPDATE language_cards SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return get_language_card(card_id)

def delete_language_card(card_id):
    conn = get_db()
    conn.execute("DELETE FROM language_cards WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()


# ── Statistics ───────────────────────────────────────────────────

def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) as n FROM cards").fetchone()['n']
    today = date.today().isoformat()
    due = conn.execute(
        "SELECT COUNT(*) as n FROM cards WHERE next_review <= ?", (today,)
    ).fetchone()['n']
    avg = conn.execute(
        "SELECT AVG(avg_rating) as a FROM cards WHERE review_count > 0"
    ).fetchone()['a']
    conn.close()
    return {
        "total": total,
        "due": due,
        "avg_rating": round(avg, 2) if avg else 0
    }
