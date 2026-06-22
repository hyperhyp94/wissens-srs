"""
KI-Erklärungsgenerierung via OpenRouter API.
Generiert 3 Erklärungsstufen: kurz, kompakt, ausfuehrlich + Titel.
Bei fehlendem API-Key oder Fehler → None (kein Dummy-Fallback).
"""
import json
import os
import urllib.request
import urllib.error

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")

SYSTEM_PROMPT = """Du bist ein exzellenter Wissensvermittler mit jahrelanger Erfahrung in Didaktik.
Deine Erklärungen sind FAKTENBASIERT, PRÄZISE und dem Niveau angepasst.
Du erklärst MECHANISMEN, ZUSAMMENHÄNGE und URSACHE-WIRKUNG.
Antworte NUR mit einem gültigen JSON-Objekt. Kein Markdown."""

EXPLANATION_PROMPT = """Erkläre das folgende Thema auf drei Niveaustufen.

Thema: {topic}

## kurz (Kurz & Knapp)
Maximal 2-3 knackige Sätze. NUR die Kernaussage.
KEINE Einleitungen wie "In der..." oder "Wenn man..." — direkt zur Sache.
Gut-Beispiel für "Photosynthese": "Pflanzen wandeln mit Chlorophyll Sonnenlicht in Zucker um. Dabei nehmen sie CO₂ auf und geben Sauerstoff ab. Ohne diesen Prozess gäbe es kein Leben auf der Erde."

## kompakt (Kompakt)
4-6 Sätze, die den Prozess gut abdecken. Mit Fachbegriffen und Zusammenhängen.
Gut-Beispiel für "Photosynthese": "Die Photosynthese findet in den Chloroplasten der Pflanzenzellen statt. Das Chlorophyll absorbiert Lichtenergie, die im Calvin-Zyklus zur Fixierung von CO₂ genutzt wird. Es entstehen Glucose und Sauerstoff. Dieser Prozess ist die primäre Energiequelle fast aller Ökosysteme."

## ausfuehrlich (Ausführlich)
8-12 Sätze, tiefgehend, wissenschaftlich. Mit Terminologie, aktueller Forschung.
Gut-Beispiel für "Photosynthese": "Die oxygenische Photosynthese gliedert sich in die Lichtreaktion und den Calvin-Zyklus. In der Lichtreaktion spalten Photosystem II und I Wasser in Protonen, Elektronen und Sauerstoff. Die Elektronen fließen durch die Cytochrom-b₆f-Komplexe und erzeugen einen Protonengradienten, der die ATP-Synthase antreibt. Im Calvin-Zyklus wird CO₂ durch das Enzym RuBisCO fixiert..."

Gib deine Antwort als JSON:
{{"title": "Prägnanter Titel (max 5 Wörter)", "kurz": "...", "kompakt": "...", "ausfuehrlich": "..."}}"""


def _call_openrouter(topic):
    """OpenRouter API aufrufen, Erklärungen + Titel generieren."""
    if not OPENROUTER_KEY:
        return None

    prompt = EXPLANATION_PROMPT.format(topic=topic)

    payload = json.dumps({
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 2000,
        "temperature": 0.5
    }).encode()

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5111",
            "X-Title": "Wissens-SRS"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"].strip()
            # Strip markdown code fences if present
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:])
                if content.endswith("```"):
                    content = content[:-3].strip()
            return json.loads(content)
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"[ai] OpenRouter error: {e}")
        return None


def generate_explanations(topic):
    """
    Erklärungen + Titel für ein Topic generieren (mit Caching).

    Returns:
        dict mit keys: title, kurz, kompakt, ausfuehrlich
        oder None bei fehlendem Key / API-Fehler
    """
    # 1. Cache prüfen
    from database import get_explanations
    cached = get_explanations(topic)
    if all(k in cached and cached[k] for k in ('kurz', 'kompakt', 'ausfuehrlich')):
        return {
            'title': topic,
            'kurz': cached['kurz'],
            'kompakt': cached['kompakt'],
            'ausfuehrlich': cached['ausfuehrlich'],
        }

    # 2. API aufrufen
    if not OPENROUTER_KEY:
        return None

    result = _call_openrouter(topic)
    if result is None or not isinstance(result, dict):
        return None

    # 3. Pflichtfelder prüfen
    required = ('title', 'kurz', 'kompakt', 'ausfuehrlich')
    if not all(k in result and result[k] for k in required):
        print(f"[ai] Unvollständige Antwort: {list(result.keys())}")
        return None

    # 4. Erklärungen cachen (ohne title, da nicht im Schema)
    from database import save_explanations
    save_explanations(topic, {
        'kurz': result['kurz'],
        'kompakt': result['kompakt'],
        'ausfuehrlich': result['ausfuehrlich'],
    })

    return result
