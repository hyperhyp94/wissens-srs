"""
Wissens-SRS Database Layer
SQLite mit allen CRUD-Operationen für Karten, Tags, Sprachkarten und Review-Log.
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

def _table_exists(conn, name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None

def _migrate_levels(conn, table, old_levels, new_levels):
    """CHECK-Constraint via Table-Rebuild migrieren."""
    if not _table_exists(conn, table):
        return
    # Prüfe ob alte Levels noch da sind
    row = conn.execute(f"SELECT DISTINCT level FROM {table} LIMIT 1").fetchone()
    if not row:
        return
    # Nimm das alte CREATE Statement
    cols = [r['name'] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    mapping = dict(zip(old_levels, new_levels))
    
    # Check ob bereits neue Levels verwendet werden
    sample = row[0]
    if sample in new_levels:
        return  # bereits migriert
    
    # Migration durchführen
    col_defs = ", ".join(
        f"{r['name']} {r['type']}" +
        (" NOT NULL" if r['notnull'] else "") +
        (" DEFAULT " + repr(r['dflt_value']) if r['dflt_value'] else "") +
        (f" CHECK(level IN {tuple(new_levels)!r})" if r['name'] == 'level' else "") +
        (" REFERENCES cards(id) ON DELETE CASCADE" if r['name'] == 'card_id' and table == 'card_tags' else "") +
        (" REFERENCES tags(id) ON DELETE CASCADE" if r['name'] == 'tag_id' and table == 'card_tags' else "")
        for r in conn.execute(f"PRAGMA table_info({table})").fetchall()
    )
    
    conn.execute(f"SAVEPOINT mig_level_{table}")
    try:
        conn.execute(f"CREATE TABLE {table}_new ({col_defs})")
        case_expr = "CASE level " + " ".join(f"WHEN '{k}' THEN '{v}'" for k,v in mapping.items()) + f" ELSE '{new_levels[0]}' END"
        conn.execute(f"INSERT INTO {table}_new SELECT *, {case_expr} FROM {table}")
        conn.execute(f"DROP TABLE {table}")
        conn.execute(f"ALTER TABLE {table}_new RENAME TO {table}")
        conn.execute(f"RELEASE mig_level_{table}")
    except Exception:
        conn.execute("ROLLBACK TO mig_level_{table}")
        raise

def init_db():
    """Tabellen erstellen (idempotent) inkl. Migration."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cards (
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
        );
        
        CREATE TABLE IF NOT EXISTS explanations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            topic_hash TEXT NOT NULL,
            level TEXT NOT NULL CHECK(level IN ('kurz','kompakt','ausfuehrlich')),
            explanation TEXT NOT NULL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(topic_hash, level)
        );
        
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS card_tags (
            card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
            tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY(card_id, tag_id)
        );
        
        CREATE TABLE IF NOT EXISTS language_cards (
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
        );
        
        CREATE TABLE IF NOT EXISTS review_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER,
            card_type TEXT DEFAULT 'knowledge',
            rating INTEGER NOT NULL CHECK(rating BETWEEN 0 AND 5),
            reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_cards_next_review ON cards(next_review);
        CREATE INDEX IF NOT EXISTS idx_cards_level ON cards(level);
        CREATE INDEX IF NOT EXISTS idx_explanations_hash ON explanations(topic_hash);
        CREATE INDEX IF NOT EXISTS idx_card_tags_card ON card_tags(card_id);
        CREATE INDEX IF NOT EXISTS idx_card_tags_tag ON card_tags(tag_id);
        CREATE INDEX IF NOT EXISTS idx_language_next_review ON language_cards(next_review);
        CREATE INDEX IF NOT EXISTS idx_review_log_card ON review_log(card_id, card_type);
    """)
    
    # Migration: Alte Level-Werte ummappen
    _migrate_levels(conn, "cards", ("easy","gruendlich","experte"), ("kurz","kompakt","ausfuehrlich"))
    _migrate_levels(conn, "explanations", ("easy","gruendlich","experte"), ("kurz","kompakt","ausfuehrlich"))
    
    # title-Spalte nachtragen falls nicht vorhanden (für Bestands-DBs)
    cols = [r['name'] for r in conn.execute("PRAGMA table_info(cards)").fetchall()]
    if 'title' not in cols:
        conn.execute("ALTER TABLE cards ADD COLUMN title TEXT")
    
    conn.commit()
    conn.close()


# ── Cards CRUD ──────────────────────────────────────────────────

def create_card(topic, explanation, level, title=None):
    """Neue SRS-Karte anlegen."""
    conn = get_db()
    today = date.today().isoformat()
    if not title:
        title = topic
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
    conn = get_db()
    rows = conn.execute("""
        SELECT c.*, GROUP_CONCAT(t.name, ',') as tag_names
        FROM cards c
        LEFT JOIN card_tags ct ON c.id = ct.card_id
        LEFT JOIN tags t ON ct.tag_id = t.id
        GROUP BY c.id
        ORDER BY c.created_at DESC
    """).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d['tags'] = d.pop('tag_names').split(',') if d.get('tag_names') else []
        result.append(d)
    return result

def get_due_cards():
    conn = get_db()
    today = date.today().isoformat()
    rows = conn.execute(
        "SELECT * FROM cards WHERE next_review <= ? ORDER BY next_review ASC",
        (today,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_card(card_id, **kwargs):
    allowed = {'ease_factor', 'interval_days', 'repetitions', 'next_review',
               'last_reviewed', 'review_count', 'avg_rating', 'title', 'topic', 'explanation'}
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


# ── Tags CRUD ───────────────────────────────────────────────────

def get_all_tags():
    conn = get_db()
    rows = conn.execute("""
        SELECT t.id, t.name, COUNT(ct.card_id) as card_count
        FROM tags t
        LEFT JOIN card_tags ct ON t.id = ct.tag_id
        GROUP BY t.id
        ORDER BY t.name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_tag_to_card(card_id, tag_name):
    conn = get_db()
    # Tag ggf. anlegen
    cur = conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name.strip().lower(),))
    tag = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name.strip().lower(),)).fetchone()
    if not tag:
        conn.close()
        return {"error": "Tag konnte nicht angelegt werden"}
    # Verbindung herstellen
    conn.execute("INSERT OR IGNORE INTO card_tags (card_id, tag_id) VALUES (?, ?)", (card_id, tag['id']))
    conn.commit()
    conn.close()
    return {"id": tag['id'], "name": tag_name.strip().lower()}

def remove_tag_from_card(card_id, tag_id):
    conn = get_db()
    conn.execute("DELETE FROM card_tags WHERE card_id = ? AND tag_id = ?", (card_id, tag_id))
    conn.commit()
    conn.close()

def get_card_tags(card_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT t.id, t.name FROM tags t
        JOIN card_tags ct ON t.id = ct.tag_id
        WHERE ct.card_id = ?
    """, (card_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Explanations CRUD ───────────────────────────────────────────

def save_explanations(topic, explanations_dict):
    """explanations_dict: {'kurz': '...', 'kompakt': '...', 'ausfuehrlich': '...'}"""
    import hashlib
    topic_hash = hashlib.md5(topic.strip().lower().encode()).hexdigest()[:12]
    conn = get_db()
    for level, text in explanations_dict.items():
        if level in ('kurz', 'kompakt', 'ausfuehrlich'):
            conn.execute(
                "INSERT OR REPLACE INTO explanations (topic, topic_hash, level, explanation) VALUES (?, ?, ?, ?)",
                (topic, topic_hash, level, text)
            )
    conn.commit()
    conn.close()

def get_explanations(topic):
    import hashlib
    topic_hash = hashlib.md5(topic.strip().lower().encode()).hexdigest()[:12]
    conn = get_db()
    rows = conn.execute(
        "SELECT level, explanation FROM explanations WHERE topic_hash = ?", (topic_hash,)
    ).fetchall()
    conn.close()
    return {r['level']: r['explanation'] for r in rows}


# ── Language Cards CRUD ─────────────────────────────────────────

def create_language_card(source_text, target_text, source_lang='de', target_lang='en', level='einfach'):
    conn = get_db()
    today = date.today().isoformat()
    cur = conn.execute(
        "INSERT INTO language_cards (source_text, target_text, source_lang, target_lang, level, next_review) VALUES (?, ?, ?, ?, ?, ?)",
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
        "SELECT * FROM language_cards WHERE next_review <= ? ORDER BY next_review ASC", (today,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_language_card(card_id, **kwargs):
    allowed = {'ease_factor', 'interval_days', 'repetitions', 'next_review',
               'last_reviewed', 'review_count', 'avg_rating', 'target_text'}
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


# ── Review Log ──────────────────────────────────────────────────

def add_review(card_id, rating, card_type='knowledge'):
    conn = get_db()
    conn.execute(
        "INSERT INTO review_log (card_id, card_type, rating) VALUES (?, ?, ?)",
        (card_id, card_type, rating)
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
    lang_total = conn.execute("SELECT COUNT(*) as n FROM language_cards").fetchone()['n']
    lang_due = conn.execute(
        "SELECT COUNT(*) as n FROM language_cards WHERE next_review <= ?", (today,)
    ).fetchone()['n']
    conn.close()
    return {
        "total": total,
        "due": due,
        "avg_rating": round(avg, 2) if avg else 0,
        "language_total": lang_total,
        "language_due": lang_due
    }
