"""
KI-Erklärungsgenerierung via OpenRouter API.
Generiert 3 Erklärungsstufen: kurz (Kurz & Knapp), kompakt, ausfuehrlich (Ausführlich).
"""
import json
import os
import urllib.request
import urllib.error

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")

SYSTEM_PROMPT = """Du bist ein exzellenter Wissensvermittler mit jahrelanger Erfahrung in Didaktik.
Deine Erklärungen sind FAKTENBASIERT, PRÄZISE und dem Niveau angepasst.
Du erklärst MECHANISMEN, ZUSAMMENHÄNGE und URSACHE-WIRKUNG.
KEINE Einleitungen, KEINE Floskeln, KEIN Baby-Talk.
Antworte NUR mit einem gültigen JSON-Objekt. Kein Markdown, kein Code-Block."""

EXPLANATION_PROMPT = """Erkläre das folgende Thema auf drei Niveaustufen.

Thema: {topic}

## kurz (Kurz & Knapp)
Maximal 2-3 knackige Sätze. NUR die Kernaussage.
Direkt zur Sache, keine Einleitung.
Gut-Beispiel für "Photosynthese": "Pflanzen wandeln mit Chlorophyll Sonnenlicht in Zucker um. Dabei nehmen sie CO₂ auf und geben Sauerstoff ab. Ohne diesen Prozess gäbe es kein Leben auf der Erde."

## kompakt (Kompakt)
4-6 Sätze, die den Prozess gut abdecken. Mit Fachbegriffen und Zusammenhängen.
Gut-Beispiel für "Photosynthese": "Die Photosynthese findet in den Chloroplasten der Pflanzenzellen statt. Das Chlorophyll absorbiert Lichtenergie, die im Calvin-Zyklus zur Fixierung von CO₂ genutzt wird. Es entstehen Glucose und Sauerstoff. Dieser Prozess ist die primäre Energiequelle fast aller Ökosysteme."

## ausfuehrlich (Ausführlich)
8-12 Sätze, tiefgehend, wissenschaftlich. Mit Terminologie und Zusammenhängen.
Gut-Beispiel für "Photosynthese": "Die oxygenische Photosynthese gliedert sich in Lichtreaktion und Calvin-Zyklus. In der Lichtreaktion spalten Photosystem II und I Wasser in Protonen, Elektronen und Sauerstoff. Der Elektronenfluss erzeugt einen Protonengradienten, der die ATP-Synthase antreibt. Im Calvin-Zyklus wird CO₂ durch RuBisCO fixiert und zu Triosephosphaten reduziert."

Gib deine Antwort NUR als JSON (kein Markdown, kein Code-Block):
{{"title": "Prägnanter Titel (max 6 Wörter)", "kurz": "...", "kompakt": "...", "ausfuehrlich": "..."}}"""

RANDOM_PROMPT = """Wähle EIN konkretes Thema aus der Kategorie "{category}" und erkläre es auf drei Niveaustufen.
Das Thema soll spezifisch und interessant sein — kein generischer Oberbegriff.
Wenn die Kategorie "Gemüse" ist, wähle z.B. "Radieschen" oder "Brokkoli", nicht "Gemüse allgemein".

Gib deine Antwort NUR als JSON (kein Markdown, kein Code-Block):
{{"topic": "Das gewählte Thema", "title": "Prägnanter Titel (max 6 Wörter)", "kurz": "...", "kompakt": "...", "ausfuehrlich": "..."}}"""

LANGUAGE_PROMPT = """Du bist ein Sprachtrainer für {target_lang}.

Modus: {mode}
Stufe: {level}

{mode_instructions}

Gib deine Antwort NUR als JSON (kein Markdown, kein Code-Block):
{{"source_text": "...", "target_text": "..."}}"""


def _call_openrouter(prompt, system=SYSTEM_PROMPT, max_tokens=1500):
    """OpenRouter API aufrufen."""
    if not OPENROUTER_KEY:
        return None

    payload = json.dumps({
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.5
    }).encode()

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://192.168.1.134:5111",
            "X-Title": "Wissens-SRS"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"]
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                if lines[0].startswith("```"):
                    content = "\n".join(lines[1:])
                if content.endswith("```"):
                    content = content[:-3].strip()
            return json.loads(content)
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"[ai] API error: {e}")
        return None


def generate_explanations(topic):
    """
    Erklärungen für ein Topic generieren (mit Caching).
    
    Returns:
        dict: {'title': '...', 'kurz': '...', 'kompakt': '...', 'ausfuehrlich': '...'}
        oder None bei Fehler
    """
    # 1. Cache prüfen (nur Erklärungen, nicht Titel)
    from database import get_explanations
    cached = get_explanations(topic)
    if cached and len(cached) == 3:
        return {"title": topic, **cached}
    
    # 2. API aufrufen
    result = _call_openrouter(EXPLANATION_PROMPT.format(topic=topic))
    if result is None:
        return None
    
    # 3. Validieren
    for key in ['kurz', 'kompakt', 'ausfuehrlich']:
        if key not in result or not result.get(key) or len(result[key]) < 30:
            return None
    
    result.setdefault('title', topic)
    
    # 4. Cachen
    from database import save_explanations
    save_explanations(topic, {k: v for k, v in result.items() if k in ('kurz', 'kompakt', 'ausfuehrlich')})
    
    return result


def generate_random(category):
    """
    Zufälliges Thema aus einer Kategorie generieren + erklären.
    
    Returns:
        dict: {'topic': '...', 'title': '...', 'kurz': '...', 'kompakt': '...', 'ausfuehrlich': '...'}
        oder None bei Fehler
    """
    result = _call_openrouter(RANDOM_PROMPT.format(category=category), max_tokens=1800)
    if result is None:
        return None
    
    for key in ['topic', 'kurz', 'kompakt', 'ausfuehrlich']:
        if key not in result or not result.get(key) or (key != 'topic' and len(result[key]) < 30):
            return None
    
    result.setdefault('title', result.get('topic', category))
    return result


def generate_language(text, target_lang='en', level='einfach', mode='translate'):
    """
    Sprach-Modus: Übersetzung oder Satzgenerierung.
    
    Args:
        text: Quelltext (bei mode='translate') oder None (bei mode='generate')
        target_lang: Zielsprache (z.B. 'en', 'fr', 'es')
        level: 'einfach', 'mittel', 'fortgeschritten'
        mode: 'translate' oder 'generate'
    
    Returns:
        dict: {'source_text': '...', 'target_text': '...'}
        oder None bei Fehler
    """
    if mode == 'translate':
        mode_instructions = f"Übersetze den folgenden {target_lang}-Text ins Deutsche. Bei jedem Niveau soll die Übersetzung dem Sprachniveau angepasst sein:\n\n{text}"
    else:
        if level == 'einfach':
            mode_instructions = f"Generiere einen einfachen Satz auf {target_lang} (Grundwortschatz, kurze Sätze) mit deutscher Übersetzung."
        elif level == 'mittel':
            mode_instructions = f"Generiere einen mittelschweren Satz auf {target_lang} (Alltagssituationen, zusammengesetzte Sätze) mit deutscher Übersetzung."
        else:
            mode_instructions = f"Generiere einen anspruchsvollen Satz auf {target_lang} (komplexe Satzstrukturen, Fachvokabular, Niveau C1-C2) mit deutscher Übersetzung."
    
    result = _call_openrouter(LANGUAGE_PROMPT.format(
        target_lang=target_lang, level=level, mode=mode,
        mode_instructions=mode_instructions
    ), max_tokens=1000)
    
    if result is None:
        return None
    
    if not result.get('source_text') or not result.get('target_text'):
        return None
    
    return result
