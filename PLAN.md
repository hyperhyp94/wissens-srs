# Wissens-SRS — Knowledge Spaced Repetition System

> **Für den Cron-Job:** Dies ist dein Bauplan. Lies diese Datei, prüfe den aktuellen Stand, und arbeite Task für Task ab. Wenn ein Task fehlschlägt, fixe den Fehler zuerst, dann mach weiter.

**Ziel:** Eine Web-App, in die man beliebige Themen/Wissensschnipsel eingibt, KI-generierte Erklärungen auf 3 Niveaustufen bekommt, die beste Erklärung auswählt und ins SRS-System (Spaced Repetition à la Anki) übernimmt. Das Wissen wird dann periodisch (1 Tag, 3 Tage, 1 Woche, 2 Wochen...) zur Wiederholung vorgelegt.

**Architektur:** Flask-Backend (server.py) + Vanilla HTML/JS Frontend (index.html) + SQLite-Datenbank + OpenRouter API für KI-Erklärungen. SM-2-Algorithmus für SRS.

**Tech Stack:** Python 3, Flask, SQLite, Tailwind CSS CDN, Vanilla JS, OpenRouter API

**Port:** 5111

---

## Datenmodell (SQLite)

### Tabelle: `cards`
```sql
CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,              -- Das ursprüngliche Thema (z.B. "Wie entstehen Wolken?")
    explanation TEXT NOT NULL,        -- Die ausgewählte Erklärung
    level TEXT NOT NULL,              -- 'easy' | 'abitur' | 'professor'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- SRS Felder (SM-2)
    ease_factor REAL DEFAULT 2.5,     -- Start-Ease (ändert sich mit Bewertungen)
    interval_days INTEGER DEFAULT 0,  -- Aktuelles Intervall in Tagen
    repetitions INTEGER DEFAULT 0,    -- Anzahl erfolgreicher Wiederholungen
    next_review DATE,                 -- Nächster Fälligkeitstermin
    last_reviewed DATE,               -- Letztes Review-Datum
    -- Metadaten
    review_count INTEGER DEFAULT 0,   -- Wie oft insgesamt reviewed
    avg_rating REAL DEFAULT 0         -- Durchschnittliche Bewertung (0-5)
);
```

### Tabelle: `explanations` (Cache für generierte Erklärungen)
```sql
CREATE TABLE explanations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER REFERENCES cards(id),
    topic TEXT NOT NULL,
    level TEXT NOT NULL,              -- 'easy' | 'abitur' | 'professor'
    explanation TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Tabelle: `review_log`
```sql
CREATE TABLE review_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER REFERENCES cards(id),
    rating INTEGER NOT NULL,          -- 0-5 (SM-2 quality)
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## API Endpoints (Flask)

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| GET | `/` | Frontend (index.html) |
| POST | `/api/generate` | Erklärungen generieren (Body: `{topic: "..."}`) |
| GET | `/api/explanations/<topic_hash>` | Generierte Erklärungen abrufen |
| POST | `/api/cards` | Karte erstellen (Body: `{topic, explanation, level}`) |
| GET | `/api/cards` | Alle Karten (mit SRS-Status) |
| GET | `/api/cards/due` | Fällige Karten für heute |
| POST | `/api/cards/<id>/review` | Karte reviewen (Body: `{rating: 0-5}`) |
| GET | `/api/stats` | Statistiken (Total, Fällig, Durchschnitt) |

---

## SM-2 Algorithmus (vereinfacht, Python)

```python
def sm2(card, rating):
    """rating: 0-5 (0=komplett vergessen, 5=perfekt erinnert)"""
    if rating >= 3:
        if card['repetitions'] == 0:
            card['interval_days'] = 1
        elif card['repetitions'] == 1:
            card['interval_days'] = 3
        else:
            card['interval_days'] = round(card['interval_days'] * card['ease_factor'])
        card['repetitions'] += 1
    else:
        card['repetitions'] = 0
        card['interval_days'] = 1
    
    # Ease-Faktor anpassen
    card['ease_factor'] = max(1.3, card['ease_factor'] + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02)))
    
    # Nächsten Review-Termin setzen
    from datetime import date, timedelta
    card['next_review'] = (date.today() + timedelta(days=card['interval_days'])).isoformat()
    card['last_reviewed'] = date.today().isoformat()
    card['review_count'] += 1
    
    return card
```

---

## UI-Design

### Seiten:
1. **Startseite / Dashboard:** Übersicht: X Karten insgesamt, Y heute fällig. Sucheingabe für neues Thema.
2. **Erklärungs-Auswahl:** Nach Themeneingabe: 3 Karten (Kinderleicht, Abitur, Professor) parallel anzeigen. User wählt eine aus → wird zur SRS-Karte.
3. **Review-Modus:** Fällige Karten nacheinander anzeigen. User liest Erklärung, bewertet dann 0-5. Nächste Karte.
4. **Bibliothek:** Alle Karten, filterbar, sortierbar.

### Mobile First! (375px Breite)
- Bottom-Navigation auf Mobile
- Karten als Stack-Layout
- Touch-Ziele min. 44×44px

---

## Bauphasen & Tasks

### Phase 0: Projekt-Grundgerüst
- [✓] **T0.1:** `server.py` mit Flask-Grundgerüst (alle Routen als Stubs)
- [✓] **T0.2:** `index.html` Grundgerüst (leere Seite mit Nav)
- [✓] **T0.3:** `META.json` anlegen
- [✓] **T0.4:** `requirements.txt` (flask)
- [✓] **T0.5:** Server starten, curl-Test: HTTP 200

### Phase 1: Datenbank & Datenmodell
- [✓] **T1.1:** `database.py` — SQLite-Init, `init_db()` Funktion, Tabellen erstellen
- [✓] **T1.2:** `database.py` — CRUD-Funktionen für cards (create, get_all, get_due, get_by_id, update, delete)
- [✓] **T1.3:** `database.py` — Funktionen für explanations (save, get_by_topic)
- [✓] **T1.4:** `database.py` — Funktion für review_log (add_entry)
- [✓] **T1.5:** Test: DB wird bei Serverstart initialisiert

### Phase 2: SRS-Algorithmus
- [✓] **T2.1:** `srs.py` — `sm2(card, rating)` Funktion
- [✓] **T2.2:** `srs.py` — Unit-Test mit bekannten SM-2 Werten
- [✓] **T2.3:** Integration in API: Review-Endpoint nutzt sm2()

### Phase 3: KI-Erklärungsgenerierung
- [✓] **T3.1:** `ai.py` — `generate_explanations(topic)` via OpenRouter API
- [✓] **T3.2:** Prompt-Engineering: 3 Niveaustufen (Kinderleicht, Abitur, Professor)
- [✓] **T3.3:** Fallback: Wenn API-Key fehlt → Dummy-Erklärungen (damit App testbar bleibt)
- [✓] **T3.4:** `/api/generate` Endpoint implementieren

### Phase 4: API-Endpunkte (echte Implementierung)
- [✓] **T4.1:** `POST /api/generate` — nimmt Topic, ruft KI, speichert Explanations, returned sie
- [✓] **T4.2:** `GET /api/explanations` — cached Explanations für Topic zurückgeben
- [✓] **T4.3:** `POST /api/cards` — Karte aus selektierter Explanation erstellen
- [✓] **T4.4:** `GET /api/cards/due` — alle heute fälligen Karten
- [✓] **T4.5:** `POST /api/cards/<id>/review` — Review mit SM-2
- [✓] **T4.6:** `GET /api/stats` — Statistiken
- [✓] **T4.7:** Alle Endpunkte mit curl durchtesten

### Phase 5: Frontend — Dashboard
- [✓] **T5.1:** Dashboard-Layout: Stats-Karten oben, "Neues Thema"-Input
- [✓] **T5.2:** Stats live von `/api/stats` laden
- [✓] **T5.3:** "Fällige Karten"-Sektion (falls due > 0)
- [✓] **T5.4:** Mobile-optimiert (Bottom-Nav)

### Phase 6: Frontend — Erklärungsauswahl
- [✓] **T6.1:** Nach Themeneingabe: Loading-Spinner, dann 3 Erklärungskarten
- [✓] **T6.2:** Jede Karte zeigt: Level-Label, Erklärungstext, "Auswählen"-Button
- [✓] **T6.3:** Bei Auswahl: Karte wird per API erstellt, Redirect zum Dashboard
- [✓] **T6.4:** Error-Handling (API down, keine Erklärungen, etc.)

### Phase 7: Frontend — Review-Modus
- [✓] **T7.1:** Review-Seite: zeigt eine Karte (Erklärung lesen)
- [✓] **T7.2:** Nach Lesen: "Aufdecken"-Button → Bewertungs-Buttons (0-5)
- [✓] **T7.3:** Bei Bewertung: API-Call, nächste Karte laden
- [✓] **T7.4:** "Keine weiteren Karten"-State
- [✓] **T7.5:** Mobile: Swipe-Gesten? Oder große Tasten (44px+)

### Phase 8: Frontend — Bibliothek
- [✓] **T8.1:** Alle Karten als Liste (Topic, Level, nächster Review)
- [✓] **T8.2:** Suche/Filter (nach Topic, Level)
- [✓] **T8.3:** Karte löschen können

### Phase 9: Polish & Testing
- [✓] **T9.1:** Responsive Design verfeinern (iPhone SE 375px)
- [ ] **T9.2:** Dark Mode? (optional)
- [ ] **T9.3:** Alle Edge Cases testen
- [ ] **T9.4:** Performance: DB-Indizes prüfen
- [ ] **T9.5:** README.md schreiben

---

## Status-Legende
- `[ ]` = nicht gestartet
- `[~]` = in Arbeit
- `[✓]` = fertig
- `[✗]` = fehlgeschlagen (muss gefixt werden)

---

## OpenRouter API Prompt-Template

```
System: Du bist ein Wissensvermittler. Erkläre das folgende Thema auf drei verschiedenen Niveaustufen.
Antworte NUR mit einem JSON-Objekt:

{
  "easy": "Erklärung für ein 8-jähriges Kind. Einfache Worte, bildhaft, kurz (2-3 Sätze).",
  "abitur": "Erklärung auf Abitur-Niveau. Fachbegriffe erklärt, logischer Aufbau (4-6 Sätze).",
  "professor": "Erklärung auf Universitäts-Niveau. Wissenschaftlich präzise, mit Fachterminologie (6-10 Sätze)."
}

Thema: {topic}
```

---

## Fortschritt (wird vom Cron-Job aktualisiert)

**Letzter Run:** 22.06.2026 14:51 (manuell)
**Aktuelle Phase:** 9 (Polish)
**Nächster Task:** T9.1
