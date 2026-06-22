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

LANGUAGE_TRANSLATE_PROMPT = """Du bist ein Sprachtrainer für {target_lang}. Übersetze den folgenden deutschen Text.

Stufe: {level}

## Stufen-Anforderungen

### Einfach (A1-A2)
- Grundwortschatz (max 500 häufigste Wörter).
- Kurze, einfache Sätze (Subjekt-Prädikat-Objekt, keine Nebensätze).
- Keine Idiome, keine Passivkonstruktionen.
- Gut-Beispiel (DE→EN, "einfach"):
  Eingabe: "Ich möchte ein Glas Wasser bestellen."
  Ausgabe: {{"source_text": "Ich möchte ein Glas Wasser bestellen.", "target_text": "I would like to order a glass of water."}}

### Mittel (B1-B2)
- Alltagssprache mit Nebensätzen (weil, obwohl, dass).
- Module Hilfsverben, Konjunktiv II, typische Phrasen.
- Keine fachspezifischen Begriffe oder seltene Idiome.
- Gut-Beispiel (DE→EN, "mittel"):
  Eingabe: "Obwohl es geregnet hat, bin ich trotzdem zum Training gegangen."
  Ausgabe: {{"source_text": "Obwohl es geregnet hat, bin ich trotzdem zum Training gegangen.", "target_text": "Although it was raining, I still went to the training session."}}

### Fortgeschritten (C1-C2)
- Komplexe Satzstrukturen (Schachtelsätze, Partizipialkonstruktionen).
- Differenziertes Vokabular, Kollokationen, Nuancierungen.
- Auch idiomatische Wendungen und fachspezifische Begriffe, wenn zum Thema passend.
- Gut-Beispiel (DE→EN, "fortgeschritten"):
  Eingabe: "Die wirtschaftlichen Verflechtungen zwischen den beiden Ländern haben sich in den letzten Jahrzehnten zunehmend diversifiziert."
  Ausgabe: {{"source_text": "Die wirtschaftlichen Verflechtungen zwischen den beiden Ländern haben sich in den letzten Jahrzehnten zunehmend diversifiziert.", "target_text": "The economic interconnections between the two countries have become increasingly diversified over the past decades."}}

Text zum Übersetzen:
{text}

Antworte NUR als JSON: {{"source_text": "Deutscher Originaltext", "target_text": "{target_lang}-Übersetzung (dem Niveau angepasst)"}}"""

LANGUAGE_GENERATE_PROMPT = """Du bist ein Sprachtrainer für {target_lang}. Generiere einen Satz auf {target_lang} mit deutscher Übersetzung.

Stufe: {level}

## Stufen-Anforderungen

### Einfach (A1-A2)
- Grundwortschatz, kurze Sätze (3-8 Wörter).
- Alltagsthemen (Essen, Wetter, Familie, Einkaufen, Hobbys).
- Keine Idiome, keine komplexe Grammatik.
- Gut-Beispiel (FR, "einfach"):
  Ausgabe: {{"source_text": "Le chat est sur la table.", "target_text": "Die Katze ist auf dem Tisch."}}

### Mittel (B1-B2)
- Alltagssituationen (Arztbesuch, Reiseplanung, Smalltalk, Bewerbung).
- Nebensätze, zusammengesetzte Satzstrukturen.
- Typische Redemittel für die Situation.
- Gut-Beispiel (ES, "mittel"):
  Ausgabe: {{"source_text": "Aunque no tengo mucha experiencia, estoy seguro de que puedo aprender rápido si me dan la oportunidad.", "target_text": "Obwohl ich nicht viel Erfahrung habe, bin ich mir sicher, dass ich schnell lernen kann, wenn man mir die Chance gibt."}}

### Fortgeschritten (C1-C2)
- Komplexe, abstrakte Themen (Politik, Wirtschaft, Wissenschaft, Kultur).
- Differenzierte Argumentation, hypothetische Konstruktionen.
- Fachvokabular und nuancierte Ausdrucksweise.
- Gut-Beispiel (EN, "fortgeschritten"):
  Ausgabe: {{"source_text": "The government's proposed fiscal policy, while ostensibly aimed at stimulating economic growth, fails to address the underlying structural issues that have long plagued the manufacturing sector.", "target_text": "Die vorgeschlagene Fiskalpolitik der Regierung zielt zwar vordergründig auf die Ankurbelung des Wirtschaftswachstums ab, versäumt es jedoch, die strukturellen Probleme anzugehen, die den Fertigungssektor seit Langem plagen."}}

Antworte NUR als JSON: {{"source_text": "Generierter {target_lang}-Satz", "target_text": "Deutsche Übersetzung"}}"""


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
        prompt = LANGUAGE_TRANSLATE_PROMPT.format(
            target_lang=target_lang, level=level, text=text
        )
    else:
        prompt = LANGUAGE_GENERATE_PROMPT.format(
            target_lang=target_lang, level=level
        )
    
    result = _call_openrouter(prompt, max_tokens=1000)
    
    if result is None:
        return None
    
    if not result.get('source_text') or not result.get('target_text'):
        return None
    
    return result
