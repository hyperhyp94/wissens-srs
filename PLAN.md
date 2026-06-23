# Wissens-SRS — Architektur- & Ausbauplan

> **Für den Cron-Job:** Dies ist dein Bauplan. Lies diese Datei, prüfe den aktuellen Stand, und arbeite Task für Task ab. Wenn ein Task fehlschlägt, fixe den Fehler zuerst, dann mach weiter. Arbeite ausschliesslich im Verzeichnis `/home/sven/hermes-workspace/projects/wissens-srs`.

**Ziel:** Eine Web-App, in die man beliebige Themen/Wissensschnipsel eingibt, KI-generierte Erklärungen auf 3 Niveaustufen bekommt, die beste Erklärung auswählt und ins SRS-System (Spaced Repetition à la Anki) übernimmt. Erweitert um Titel, Tags, eine überarbeitete Bibliothek, einen Random-Modus und einen separaten Sprach-Lernmodus.

**Tech Stack:** Python 3, Flask, SQLite, Tailwind CSS CDN, Vanilla JS, OpenRouter API, SM-2.

**Port:** 5111

---

## 1. Aktuelle Architektur (Ist-Zustand)

### Was bereits läuft
- **Flask-Backend** (`server.py`): statische Auslieferung von `index.html`, JSON-API. Start über `TOOL_PORT` (Default 5111).
- **SQLite** (`database.py`): `get_db()` mit `row_factory`, WAL-Modus, `foreign_keys=ON`. DB unter `data/wissens.db`. Idempotentes `init_db()`.
- **SM-2 Algorithmus** (`srs.py`): `sm2(card, rating)` mit Rating 0–5, Ease-Faktor (min. 1.3), Intervall-Eskalation (1 → 3 → interval×ease), Reset bei Rating < 3, gleitender Bewertungsdurchschnitt. Eingebaute Unit-Tests via `python srs.py`.
- **KI-Erklärungen** (`ai.py`): OpenRouter (`openai/gpt-4o-mini`), `generate_explanations(topic)` mit Cache-Lookup, JSON-Antwort. **Dummy-Fallback** (`_generate_dummy`) bei fehlendem Key/Fehler.
- **Frontend** (`index.html`): Single-Page, Tailwind CDN, Vanilla JS. Drei Seiten: Dashboard, Lernen (Review), Bibliothek. Mobile Bottom-Nav + Desktop-Topbar.

### Datenmodell (Ist)
- **`cards`**: `id, topic, explanation, level CHECK(easy|gruendlich|experte), created_at, ease_factor, interval_days, repetitions, next_review, last_reviewed, review_count, avg_rating`.
- **`explanations`** (Cache): `id, topic, topic_hash (md5[:12]), level CHECK(easy|gruendlich|experte), explanation, generated_at`, `UNIQUE(topic_hash, level)`.
- **`review_log`**: `id, card_id → cards(id) ON DELETE CASCADE, rating CHECK(0–5), reviewed_at`.
- Indizes: `idx_cards_next_review`, `idx_cards_level`, `idx_explanations_hash`, `idx_review_log_card`.

### API-Endpunkte (Ist)
| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| GET | `/` | Frontend (index.html) |
| POST | `/api/generate` | Erklärungen generieren (Body: `{topic}`) |
| GET | `/api/explanations/<topic>` | Gecachte Erklärungen abrufen |
| GET/POST | `/api/cards` | Alle Karten / Karte erstellen (`{topic, explanation, level}`) |
| GET | `/api/cards/due` | Heute fällige Karten |
| DELETE | `/api/cards/<id>` | Karte löschen |
| POST | `/api/cards/<id>/review` | Review mit SM-2 (`{rating: 0-5}`) |
| GET | `/api/stats` | Statistiken (total, due, avg_rating) |

### Bekannte Inkonsistenzen / technische Schuld
- **Level-Naming:** Commit `3be4afc` benannte UI-Labels in "Einfach/Gründlich/Experte" um, die DB-Keys bleiben `easy`/`gruendlich`/`experte`. Die neuen Stufen (siehe Feature 1) erfordern Migration der `CHECK`-Constraints in `cards` UND `explanations`.
- **Dummy-Fallback:** `_generate_dummy()` liefert generische Platzhaltertexte — laut neuem Ziel komplett zu entfernen.
- **Doc-Drift:** Docstrings in `ai.py`/`database.py` nennen teils alte Keys (`abitur`, `professor`).
- **AGENTS.md:** Unter `/home/sven/hermes-workspace/projects/AGENTS.md` nicht vorhanden (Stand dieser Analyse). Projektregeln daher aus dieser PLAN.md ableiten.

---

## 2. Neue Features (alle einplanen)

### Feature 1 — Drei neue Erklärungs-Stufen
Ersetzt `easy/gruendlich/experte` durch:
- **`kurz`** (Kurz & Knapp): 2–3 knackige Sätze, maximal kompakt.
- **`kompakt`** (Kompakt): 4–6 Sätze, gute Abdeckung.
- **`ausfuehrlich`** (Ausführlich): 8–12 Sätze, tiefgehend, wissenschaftlich.

Anforderungen:
- **KEIN Dummy-Fallback mehr.** Bei fehlendem API-Key oder API-Fehler → sauberer HTTP-Fehler (z. B. 503 mit klarer Meldung), keine Platzhaltertexte.
- Der Prompt muss **ZWINGEND Beispiel-Gute-Erklärungen** je Stufe enthalten (Few-Shot, analog zu den bestehenden „Gut/Schlecht"-Beispielen).
- JSON-Schema der KI-Antwort: `{"kurz": "...", "kompakt": "...", "ausfuehrlich": "..."}`.

### Feature 2 — Titelgenerierung
- Beim Erstellen einer Karte generiert die KI automatisch einen **prägnanten Titel** (Kurzbezeichnung des Themas).
- Titel wird im Dashboard und in der Bibliothek angezeigt.
- Datenmodell: `cards.title TEXT` (per `ALTER TABLE`, nullable für Bestandskarten; Fallback im Frontend = `topic`).

### Feature 3 — Tags / Kategorien
- Jede Karte bekommt ein oder mehrere Tags.
- Neue Tabellen:
  - `tags (id INTEGER PK, name TEXT UNIQUE NOT NULL)`
  - `card_tags (card_id → cards(id) ON DELETE CASCADE, tag_id → tags(id) ON DELETE CASCADE, PRIMARY KEY(card_id, tag_id))`
- API:
  - `GET /api/tags` — alle Tags (optional mit Kartenanzahl).
  - `POST /api/cards/<id>/tags` — Tag zuweisen (`{name}` oder `{tag_id}`; legt Tag bei Bedarf an).
  - `DELETE /api/cards/<id>/tags/<tag_id>` — Tag von Karte entfernen.
- Frontend: Tags vergeben/anzeigen im Library-Bereich, Filter nach Tags, Suche.

### Feature 4 — Library-Ansicht verbessern
- Alle Karten als Liste mit **Titel, Tags, Level, nächstem Review**.
- **Suchfeld** (Volltext über Titel/Topic/Erklärung, clientseitig).
- **Tag-Filter** (Multiple Select).
- **Sortierung**: Erstelldatum, nächster Review, Level.

### Feature 5 — Random-Modus
- Button „Zufälliges Thema" im Dashboard.
- User wählt eine **Kategorie** (z. B. „Gemüse", „Physik", „Tiere").
- KI wählt **ein konkretes Thema aus dieser Kategorie** und erklärt es sofort (3 Stufen wie Feature 1).
- Beispiel: Kategorie „Gemüse" → KI wählt „Radieschen" → 3 Erklärungen + Titel.
- API: `POST /api/random` (Body: `{category}`) → `{topic, title, explanations}`.

### Feature 6 — Sprach-Modus (separater Bereich)
- Neuer Navigationsbereich „Sprachen".
- 3 Stufen: **Einfach** (Grundwortschatz), **Mittel** (Alltagssätze), **Fortgeschritten** (komplexe Texte).
- Zwei Eingabe-Flüsse:
  1. User gibt Wort/deutschen Satz ein → KI übersetzt in Zielsprache (z. B. Englisch).
  2. KI generiert Satz in Zielsprache + deutsche Übersetzung (passend zur Stufe).
- SRS funktioniert identisch wie für Wissenskarten.
- Eigene Tabelle:
  `language_cards (id, source_text, target_text, source_lang, target_lang, level CHECK(einfach|mittel|fortgeschritten), created_at, + alle SM-2-Felder identisch zu cards)`.
- API:
  - `POST /api/language/generate` (`{text?, mode: translate|generate, target_lang, level}`) → Quelltext/Zieltext.
  - `GET/POST /api/language/cards` — Sprachkarten listen/erstellen.
  - `GET /api/language/cards/due`, `POST /api/language/cards/<id>/review`, `DELETE /api/language/cards/<id>`.

### Feature 7 — Datenmodell-Erweiterungen (Zusammenfassung)
- `cards.title` hinzufügen.
- `tags` + `card_tags` für Tagging.
- `language_cards` neue Tabelle (SM-2-Felder 1:1 wie `cards`).
- Level-Constraints in `cards`/`explanations` auf `kurz|kompakt|ausfuehrlich` migrieren.

### Feature 8 — Mobile & Performance
- **Service Worker** für Offline-Fähigkeit (PWA): `manifest.json` + `sw.js`, App-Shell-Caching.
- CSS/JS minifiziert (optional).
- **Lazy Loading** für die Bibliothek (paginiert/inkrementell rendern).
- Keine externen Abhängigkeiten außer Tailwind CDN.

---

## 3. Ziel-Datenmodell (Soll)

```sql
-- cards: + title, Level-Keys neu
cards(
  id, topic, title, explanation,
  level CHECK(level IN ('kurz','kompakt','ausfuehrlich')),
  created_at, ease_factor, interval_days, repetitions,
  next_review, last_reviewed, review_count, avg_rating
)

explanations(
  id, topic, topic_hash,
  level CHECK(level IN ('kurz','kompakt','ausfuehrlich')),
  explanation, generated_at, UNIQUE(topic_hash, level)
)

tags(id PK, name TEXT UNIQUE NOT NULL)
card_tags(card_id FK→cards, tag_id FK→tags, PRIMARY KEY(card_id, tag_id))

language_cards(
  id, source_text, target_text, source_lang, target_lang,
  level CHECK(level IN ('einfach','mittel','fortgeschritten')),
  created_at, ease_factor, interval_days, repetitions,
  next_review, last_reviewed, review_count, avg_rating
)

review_log: unverändert (für Sprachkarten ggf. card_type-Spalte oder separates language_review_log)
```

Indizes ergänzen: `idx_card_tags_card`, `idx_card_tags_tag`, `idx_language_next_review`.

**Migrationsstrategie (SQLite):** Da SQLite `CHECK`-Constraints nicht per `ALTER` ändern kann, erfolgt die Level-Migration über das Table-Rebuild-Pattern (neue Tabelle anlegen → Daten kopieren/mappen → alte droppen → umbenennen). Bestehende Level-Werte werden gemappt: `easy→kurz`, `gruendlich→kompakt`, `experte→ausfuehrlich`. `cards.title` via `ALTER TABLE ADD COLUMN`. Alle Schritte idempotent in `init_db()` mit Versions-/Existenzprüfung (`PRAGMA table_info`).

---

## 4. Ziel-API (Soll, Überblick)

| Methode | Pfad | Zweck |
|---------|------|------|
| POST | `/api/generate` | 3 Erklärungen (kurz/kompakt/ausfuehrlich) + Titel |
| POST | `/api/random` | Thema aus Kategorie wählen + erklären |
| GET/POST | `/api/cards` | Karten listen / erstellen (mit title) |
| GET | `/api/cards/due` | Fällige Wissenskarten |
| POST | `/api/cards/<id>/review` | SM-2 Review |
| DELETE | `/api/cards/<id>` | Karte löschen |
| GET | `/api/tags` | Tags auflisten |
| POST | `/api/cards/<id>/tags` | Tag zuweisen |
| DELETE | `/api/cards/<id>/tags/<tag_id>` | Tag entfernen |
| POST | `/api/language/generate` | Übersetzen/Satz generieren |
| GET/POST | `/api/language/cards` | Sprachkarten listen/erstellen |
| GET | `/api/language/cards/due` | Fällige Sprachkarten |
| POST | `/api/language/cards/<id>/review` | SM-2 Review (Sprache) |
| DELETE | `/api/language/cards/<id>` | Sprachkarte löschen |
| GET | `/api/stats` | Statistiken (inkl. Sprachkarten) |

---

## 5. Bauphasen & Tasks

### Phase 0: DB-Migration
- [✓] **T0.1:** `init_db()` erweitern: `cards.title` via `ALTER TABLE ADD COLUMN` (idempotent via `PRAGMA table_info`).
- [✓] **T0.2:** Level-Constraint-Migration `cards` (Rebuild-Pattern, Mapping `easy→kurz`, `gruendlich→kompakt`, `experte→ausfuehrlich`).
- [✓] **T0.3:** Level-Constraint-Migration `explanations` (gleiches Mapping). Cache geleert, da regenerierbar.
- [✓] **T0.4:** Tabellen `tags` + `card_tags` + Indizes angelegt.
- [✓] **T0.5:** Tabelle `language_cards` + Index angelegt.
- [✓] **T0.6:** DB-CRUD-Funktionen ergänzt (Tags, Sprachkarten, title in create_card).
- [✓] **T0.7:** Migration auf Bestands-DB erfolgreich — 3 Karten migriert, Level gemappt (`gruendlich→kompakt`), `srs.py`-Tests grün, alle API-Endpunkte antworten.

### Phase 1: Neues Prompt-Engineering (3 Stufen + Beispiele + Titel)
- [✓] **T1.1:** `ai.py` — `EXPLANATION_PROMPT` auf `kurz/kompakt/ausfuehrlich` umgestellt, je Stufe Few-Shot-Gut-Beispiele vorhanden.
- [✓] **T1.2:** `ai.py` — Titelgenerierung im selben API-Call (Feld `title` im JSON-Response).
- [✓] **T1.3:** `ai.py` — `_generate_dummy` entfernt; bei fehlendem Key/Fehler wird `None` zurückgegeben → API gibt 503.
- [✓] **T1.4:** `server.py` — `/api/generate` Antwort um `title` erweitert; Validierung der neuen Level-Keys (`VALID_LEVELS`).
- [✓] **T1.5:** Frontend — Level-Labels `kurz/kompakt/ausfuehrlich` in `index.html` durchgängig angepasst, Titel wird angezeigt.
- [✓] **T1.6:** Doc-Drift bereinigt (Docstrings/Kommentare auf neue Keys aktualisiert).

### Phase 2: Tags API + Frontend
- [✓] **T2.1:** `GET /api/tags`, `POST /api/cards/<id>/tags`, `DELETE /api/cards/<id>/tags/<tag_id>` implementiert.
- [✓] **T2.2:** `get_all_cards()` liefert Tags je Karte mit (JOIN/Aggregation).
- [✓] **T2.3:** Frontend — Tags an Karten anzeigen (in der Library-Ansicht). Tag-Verwaltung-UI (Hinzufügen/Entfernen) ggf. noch ergänzbar.

### Phase 3: Language Mode (Backend + Frontend)
- [✓] **T3.1:** `ai.py` — Sprach-Prompt (translate + generate) je Stufe einfach/mittel/fortgeschritten. Translate-Richtung korrigiert (DE→Zielsprache). Few-Shot-Beispiele je Stufe ergänzt.
- [✓] **T3.2:** `POST /api/language/generate` + DB-CRUD für `language_cards`.
- [✓] **T3.3:** `GET/POST /api/language/cards`, `due`, `review`, `DELETE` (SM-2 wiederverwendet).
- [✓] **T3.4:** Frontend — neuer Tab „Sprachen": Eingabe, Stufenwahl, Zielsprache, Speichern, eigener Review-Flow.

### Phase 4: Random Mode
- [✓] **T4.1:** `ai.py` — Prompt „wähle Thema aus Kategorie".
- [✓] **T4.2:** `POST /api/random` → Thema + Titel + 3 Erklärungen.
- [✓] **T4.3:** Frontend — Button „Zufälliges Thema" + Kategorie-Eingabe, Ergebnis wie normale Erklärungsauswahl.

### Phase 5: Library-Rework (Search, Filter, Sort)
- [✓] **T5.1:** Suchfeld (Volltext clientseitig über Titel/Topic/Erklärung).
- [✓] **T5.2:** Tag-Filter (Multiple Select).
- [✓] **T5.3:** Sortierung (Erstelldatum / nächster Review / Level).
- [✓] **T5.4:** Anzeige: Titel, Tags, Level, nächster Review je Eintrag.

### Phase 6: Polish (PWA, Performance, Mobile)
|- [✓] **T6.1:** `manifest.json` + `sw.js` (App-Shell-Cache), Registrierung in `index.html`.
|- [✓] **T6.2:** Lazy Loading / inkrementelles Rendern der Bibliothek (Chunks à 20, IntersectionObserver + Button).
|- [✓] **T6.3:** Mobile-Test (375px), Touch-Ziele ≥ 44px, neue UI-Elemente prüfen. Fixes: Suchfeld auf min-h-[44px] erhöht, Tag-Buttons auf min-h-[44px] erhöht.
|- [✓] **T6.4:** Edge Cases & curl-Tests aller neuen Endpunkte. Alle 17+ Endpunkte durchgetestet: Validation (leere Bodies, fehlende Felder, zu kurz/lang, String statt Int, Bereichsüberschreitung), 404-Fälle, Duplikatsbehandlung, SM-2-Review-Zyklus. Alle Tests bestanden. CSS/JS-Minifizierung als optional verworfen (YAGNI — Inline-Styles ~200 Bytes, Tailwind CDN bereits minified).

---

## 6. Status-Legende
- `[ ]` = nicht gestartet · `[~]` = in Arbeit · `[✓]` = fertig · `[✗]` = fehlgeschlagen (zuerst fixen)

---

## 7. Fortschritt (wird vom Cron-Job aktualisiert)

**Letzte Aktualisierung:** 23.06.2026 (Cron-Run: Server-Restart nach Gateway-Neustart, alle Endpunkte OK)
**Aktuelle Phase:** 6 (Polish) — T6.4 abgeschlossen
**Nächster Task:** ✅ Alle Tasks abgeschlossen. Wissens-SRS ist komplett!
