# 📚 Wissens-SRS

**Knowledge Spaced Repetition System**

Gib ein beliebiges Thema ein, erhalte KI-generierte Erklärungen auf drei Niveaustufen, wähle die beste aus – und das System erinnert dich im optimalen Abstand an die Wiederholung (Spaced Repetition, SM-2 Algorithmus).

---

## Features

- **🧠 KI-Erklärungen** – OpenRouter (GPT-4o-mini) generiert drei Erklärungsstufen: Kinderleicht, Abitur, Professor
- **📅 SRS-Review** – SM-2-Algorithmus plant Wiederholungen in wachsenden Intervallen (1 Tag → 3 Tage → 1 Woche → 2 Wochen…)
- **📊 Dashboard** – Übersicht: Karten insgesamt, heute fällig, neue Themen
- **📚 Bibliothek** – Alle Karten durchsuchbar, filterbar, löschbar
- **📱 Mobile-First** – Optimiert für iPhone SE (375px), mit Bottom-Navigation und Touch-Zielen ≥44px
- **💾 Offline-Fallback** – Läuft auch ohne API-Key mit Dummy-Erklärungen

---

## Tech Stack

| Layer | Technologie |
|-------|------------|
| Backend | Python 3, Flask |
| Datenbank | SQLite (WAL-Mode) |
| Frontend | Vanilla HTML/JS, Tailwind CSS CDN |
| KI | OpenRouter API (GPT-4o-mini) |
| SRS | SM-2 Algorithmus (SuperMemo 2) |

**Kein React, kein Webpack, kein npm.** Ponytail YAGNI.

---

## Quick Start

```bash
# 1. Projekt klonen
git clone https://github.com/hyperhyp94/wissens-srs.git
cd wissens-srs

# 2. Virtuelle Umgebung + Dependencies
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 3. OPENROUTER_API_KEY setzen (optional – läuft auch ohne)
export OPENROUTER_API_KEY="sk-or-v1-..."

# 4. Server starten
./venv/bin/python server.py
# → http://localhost:5111
```

Der Server bindet auf `0.0.0.0:5111` – erreichbar von allen Geräten im LAN.

---

## API Endpoints

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| `GET` | `/` | Frontend (index.html) |
| `POST` | `/api/generate` | Erklärungen generieren → `{"topic":"..."}` |
| `GET` | `/api/explanations/<topic>` | Cached Erklärungen abrufen |
| `GET` | `/api/cards` | Alle Karten (mit SRS-Status) |
| `POST` | `/api/cards` | Karte erstellen → `{"topic","explanation","level"}` |
| `GET` | `/api/cards/due` | Heute fällige Karten |
| `DELETE` | `/api/cards/<id>` | Karte löschen |
| `POST` | `/api/cards/<id>/review` | Karte reviewen → `{"rating":0-5}` |
| `GET` | `/api/stats` | Statistiken (total, due, avg) |

### Beispiel: Thema generieren

```bash
curl -X POST http://localhost:5111/api/generate \
  -H "Content-Type: application/json" \
  -d '{"topic":"Wie entstehen Wolken?"}'
```

### Beispiel: Karte reviewen

```bash
curl -X POST http://localhost:5111/api/cards/1/review \
  -H "Content-Type: application/json" \
  -d '{"rating":4}'
```

---

## SM-2 Algorithmus

Der Spaced-Repetition-Algorithmus basiert auf Piotr Woźniaks **SuperMemo 2** (1987):

- **Bewertung 0–2 (vergessen/unsicher):** Intervall resettet auf 1 Tag, Repetitions-Zähler auf 0
- **Bewertung 3+ (erinnert):** Intervall wächst:
  - 1. Review → 1 Tag
  - 2. Review → 3 Tage
  - 3.+ Review → `interval × ease_factor`
- **Ease-Faktor** startet bei 2.5 und passt sich dynamisch an (Minimum 1.3)
- **Nächste Wiederholung** = heute + Intervall

Implementierung in `srs.py` – inklusive Unit-Tests (`python srs.py`).

---

## OpenRouter API

Die App nutzt die **OpenRouter API** mit GPT-4o-mini für Erklärungen. Kosten: ~$0.15/1M Tokens.

**Key besorgen:** [openrouter.ai/keys](https://openrouter.ai/keys)

**Key setzen:**
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

**Ohne Key:** Die App generiert einfache Dummy-Erklärungen – voll funktionsfähig zum Testen.

### Prompt-Template

Das System-Prompt fordert drei Niveaustufen an:

```
System: Du bist ein Wissensvermittler. Erkläre das Thema auf 3 Niveaustufen.
Antworte NUR mit JSON:
{
  "easy": "Für 8-Jährige – einfach, bildhaft (2–3 Sätze)",
  "abitur": "Abitur-Niveau – Fachbegriffe erklärt (4–6 Sätze)",
  "professor": "Uni-Niveau – wissenschaftlich präzise (6–10 Sätze)"
}
```

---

## Projektstruktur

```
wissens-srs/
├── server.py         # Flask-Backend (alle Routen)
├── database.py       # SQLite-Layer (CRUD, Init)
├── srs.py            # SM-2 Algorithmus + Unit-Tests
├── ai.py             # OpenRouter API + Fallback
├── index.html        # Frontend (SPA, Vanilla JS)
├── requirements.txt  # flask
├── META.json         # Registry-Metadaten
├── PLAN.md           # Bauplan (Architektur, Phasen, Tasks)
├── .gitignore        # __pycache__, venv, data/*.db
└── data/
    └── wissens.db    # SQLite-Datenbank (auto-erstellt)
```

---

## Entwicklung

- **Mobile-First:** Alle UI-Elemente funktionieren ab 375px Breite (iPhone SE)
- **PEP 668:** Immer `venv` verwenden – `python3 -m venv venv`
- **Server:** `debug=False` (Hintergrundprozess), bindet `0.0.0.0:5111`
- **Firewall:** `sudo ufw allow from 192.168.1.0/24 to any port 5111 proto tcp`
- **Keine API-Keys im Code:** `OPENROUTER_API_KEY` aus Umgebungsvariable
- **YAGNI:** Keine unnötigen Dependencies, kein npm, kein Build-Step

### Tests

```bash
# SM-2 Unit-Tests
./venv/bin/python srs.py

# Server Health Check
curl http://localhost:5111

# API Smoke Test
curl http://localhost:5111/api/stats
```

---

## Lizenz

MIT – siehe [LICENSE](LICENSE) (falls vorhanden).

---

**Gebaut mit ❤️ auf einem Raspberry Pi, orchestriert von Hermes Agent + Claude Code.**
