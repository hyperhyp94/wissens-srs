# Wissens-SRS — Verbesserungen Phase 2

## Probleme & Lösung

### 1. Bibliothek zeigt nur Wissenskarten
**Problem:** `page-library` holt nur `/api/cards`. Sprachkarten aus `/api/language/cards` fehlen.
**Lösung:** Library bekommt Tabs "Alle / Wissen / Sprache". Sprachkarten werden mit Zielsprache, Quelltext & Übersetzung angezeigt. Ein neuer API-Endpunkt `/api/library` liefert beide Typen gemischt, oder das Frontend ruft beide Endpunkte parallel ab und merged sie.

### 2. Sprach-Filter in der Bibliothek
**Problem:** Kein Filter nach Zielsprache bei Sprachkarten.
**Lösung:** Dropdown/Filter-Buttons für target_lang (DE/EN/FR/ES/IT/TR) in der Bibliothek, wenn Tab "Sprache" oder "Alle" aktiv ist.

### 3. Kategorien-Zuordnung für Sprachkarten
**Problem:** Tags (`card_tags`) existieren nur für Knowledge-Karten. Sprachkarten haben kein Tagging.
**Lösung:**
- Neue Tabelle `language_card_tags` (oder gemeinsames Tagging-System)
- Tags auch für Sprachkarten in der UI vergeben/anzeigen
- API: `POST /api/language/cards/<id>/tags`, `DELETE /api/language/cards/<id>/tags/<tag_id>`

### 4. Random-Modus verbessern
**Problem:** Kategorie muss manuell getippt werden, keine Auswahl aus bestehenden Tags.
**Lösung:**
- Dropdown mit bestehenden Tags/Kategorien (aus allen Karten, inkl. Sprachkarten)
- "Neue Kategorie" Textfeld als Option
- API bleibt gleich (`POST /api/random {category}`), aber UI bietet beides: Auswahl + Eingabe
- Zusätzlich: Kategorie-Speicherung — beim Anlegen einer Karte wird die Kategorie automatisch als Tag gespeichert

### 5. Random-Modus aus der Bibliothek
**Lösung:** "🎲 Zufälliges Thema" Button auch in der Bibliothek integrieren, oder den bestehenden Dashboard-Random-Bereich verbessern.

## Konkrete Änderungen

### backend: server.py
- `GET /api/library` → gibt beide Kartentypen gemischt zurück (jeweils mit `type: "knowledge"|"language"`)
- `GET /api/tags` → zeigt auch Tags von Sprachkarten (falls implementiert)
- `GET /api/languages` → listet alle vorhandenen target_lang-Werte aus language_cards
- Optional: Kategorien aus Tags + target_lang kombinieren

### frontend: index.html
- Library-Tabs: "Alle" | "Wissen" | "Sprache"
- Sprachfilter (target_lang Dropdown) bei Tab Sprache/Alle
- Sprachkarten-Einträge in der Library: `DE → TR: Mittagessen → öğle yemeği`
- Random-Bereich: Dropdown mit existierenden Kategorien, plus "Neue eingeben" Option
- Tags auch für Sprachkarten anlegen/entfernen

### database: database.py
- Option: gemeinsames Tagging für beide Kartentypen via Polymorphie
- Oder: `language_tags` + `language_card_tags` Tabellen
- Oder (einfacher): Tags sind universell, `card_tags` bekommt eine `card_type`-Spalte

## Datenmodell-Erweiterung (einfachste Variante)
```
card_tags: +card_type TEXT DEFAULT 'knowledge'  # knowledge oder language
```
Dann können Tags für beide Kartentypen genutzt werden, und `get_all_tags()` aggregiert über beide.

Random-Modus Kategorien: UNION aus Tags + target_lang + manuelle Eingabe.

## Test-Checkliste
- [✓] Library zeigt beide Kartentypen
- [✓] Filter nach Sprache funktioniert
- [✓] Tags lassen sich für Sprachkarten setzen
- [✓] Random-Modus: Dropdown zeigt bestehende Kategorien
- [✓] Random-Modus: Neue Kategorie eingeben funktioniert
- [✓] Random-Modus: Ergebnis kann als Karte gespeichert werden
- [✓] Keine Regression bei bestehenden Wissen-Karten

---
**Phase 2 vollständig implementiert und verifiziert (23.06.2026).**
