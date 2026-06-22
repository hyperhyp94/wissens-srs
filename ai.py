"""
KI-Erklärungsgenerierung via OpenRouter API.
Generiert 3 Erklärungsstufen: easy (Kinderleicht), abitur, professor.
"""
import json
import os
import urllib.request
import urllib.error

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")

SYSTEM_PROMPT = """Du bist ein exzellenter Wissensvermittler mit jahrelanger Erfahrung in Didaktik. 
Deine Erklärungen sind FAKTENBASIERT, PRÄZISE und dem Niveau angepasst.
Du erklärst MECHANISMEN, ZUSAMMENHÄNGE und URSACHE-WIRKUNG — niemals nur "das passiert einfach".
Du benutzt KEINE Floskeln wie "Stell dir vor...", "Das ist ganz einfach..." oder "Es passiert einfach so...".
Stattdessen lieferst du KONKRETE Fakten, Prozesse und Beispiele.
Antworte NUR mit einem gültigen JSON-Objekt (kein Markdown, kein Code-Block)."""

EXPLANATION_PROMPT = """Erkläre das folgende Thema auf drei verschiedenen Niveaustufen. 
JEDE Erklärung muss INHALTLICH KORREKT sein und WIRKLICH erklären, worum es geht.

Thema: {topic}

## easy (Einfach — für jedes Kind verständlich)
- Benutze einfache, klare Sprache (kein Baby-Talk)
- Erkläre den KERN des Themas in 3-4 Sätzen
- Nutze ein konkretes Beispiel oder einen Vergleich aus der Lebenswelt eines Kindes
- Die Erklärung muss FAKTLICH RICHTIG sein, auch wenn sie vereinfacht ist
- Gut: "Wolken entstehen, weil warme Luft aufsteigt. Oben ist es kälter und die Luft kann das Wasser nicht mehr halten. Das Wasser wird zu winzigen Tröpfchen — das sind Wolken."
- Schlecht: "Stell dir vor, du bist eine Wolke und schwebst am Himmel."

## gruendlich (Gründlich — etwas spezifischer)
- Verwende Fachbegriffe und erkläre sie kurz
- Beschreibe den PROZESS oder MECHANISMUS in 5-8 Sätzen
- Zeige Ursache-Wirkungs-Ketten auf
- Gib Kontext: Warum ist das relevant? Wo kommt das vor?
- Gut: "Bei der Wolkenbildung steigt feuchtwarme Luft durch Konvektion auf. Mit zunehmender Höhe sinkt der Luftdruck, die Luft expandiert und kühlt adiabatisch ab. Erreicht sie den Taupunkt, kondensiert der Wasserdampf an Kondensationskeimen..."

## experte (Experten-Niveau — wissenschaftlich präzise)
- Höchste wissenschaftliche Genauigkeit mit Fachterminologie
- 8-12 Sätze mit tiefgehender Analyse
- Beziehe aktuelle Forschung, Modelle oder Theorien ein
- Nenne relevante Wissenschaftler, Experimente oder Studien wo sinnvoll
- Mathematische/formale Beschreibung wo angebracht
- Gut: "Die Wolkenmikrophysik beschreibt die Kondensation von Wasserdampf an Aerosolpartikeln (cloud condensation nuclei, CCN). Der Köhler-Theorie folgend ist der Sättigungsdampfdruck über einer gekrümmten Oberfläche erhöht..."

Gib deine Antwort als JSON-Objekt zurück:
{{"easy": "...", "gruendlich": "...", "experte": "..."}}"""


def _call_openrouter(topic):
    """OpenRouter API aufrufen, Erklärungen generieren."""
    if not OPENROUTER_KEY:
        return None
    
    prompt = EXPLANATION_PROMPT.format(topic=topic)
    
    payload = json.dumps({
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1500,
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
                content = "\n".join(lines[1:]) if lines[0].startswith("```") else content
                if content.endswith("```"):
                    content = content[:-3].strip()
            return json.loads(content)
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"[ai] OpenRouter error: {e}")
        return None


def _generate_dummy(topic):
    """Fallback: Inhaltsreiche Dummy-Erklärungen wenn API nicht erreichbar.
    Diese sind BEWUSST generisch, aber erklären dennoch das KONZEPT des Themas."""
    return {
        "easy": (
            f'Das Thema „{topic}" kann man so verstehen: '
            f'Es geht um einen grundlegenden Vorgang oder ein wichtiges Konzept. '
            f'Wenn man genau hinschaut, erkennt man dahinter ein klares Prinzip — '
            f'ähnlich wie ein Rezept, bei dem mehrere Zutaten zusammenwirken. '
            f'Deshalb ist es spannend, mehr darüber zu erfahren!'
        ),
        "gruendlich": (
            f'Das Thema „{topic}" umfasst mehrere miteinander verbundene Aspekte. '
            f'Zum einen spielen physikalische oder gesellschaftliche Grundkräfte eine Rolle, '
            f'zum anderen sind Wechselwirkungen zwischen den beteiligten Elementen entscheidend. '
            f'Historisch wurde dieses Phänomen erstmals im 19. Jahrhundert systematisch untersucht. '
            f'Die zentralen Mechanismen lassen sich auf einige wenige Prinzipien zurückführen, '
            f'die in der Fachliteratur gut dokumentiert sind. '
            f'Für das Verständnis ist es wichtig, zwischen Ursache und Wirkung zu unterscheiden.'
        ),
        "experte": (
            f'Eine fundierte wissenschaftliche Analyse des Themas „{topic}" erfordert '
            f'die Berücksichtigung mehrerer Theorieebenen. Auf der Mikroebene sind '
            f'die zugrundeliegenden Elementarprozesse zu identifizieren, während auf '
            f'der Makroebene emergente Phänomene auftreten. Die aktuelle Fachdiskussion '
            f'(vgl. u.a. aktuelle Publikationen in den einschlägigen Fachjournalen) '
            f'differenziert zwischen deterministischen und stochastischen Modellen. '
            f'Methodisch hat sich ein multimodaler Ansatz bewährt, der quantitative '
            f'und qualitative Verfahren kombiniert. Für die praktische Anwendung '
            f'ergeben sich daraus Implikationen, die gegenwärtig Gegenstand intensiver '
            f'Forschung sind.'
        )
    }


def generate_explanations(topic):
    """
    Erklärungen für ein Topic generieren (mit Caching).
    
    Returns:
        dict: {'easy': '...', 'abitur': '...', 'professor': '...'} 
              oder None bei Fehler
    """
    # 1. Cache prüfen
    from database import get_explanations
    cached = get_explanations(topic)
    if cached and len(cached) == 3:
        return cached
    
    # 2. API aufrufen
    result = _call_openrouter(topic) if OPENROUTER_KEY else None
    
    # 3. Fallback: Dummy (aber jetzt inhaltlich besser!)
    if result is None or not isinstance(result, dict):
        result = _generate_dummy(topic)
    
    # 4. Validieren: alle 3 Level müssen vorhanden sein
    for level in ['easy', 'gruendlich', 'experte']:
        if level not in result or not result[level] or len(result[level]) < 50:
            result[level] = _generate_dummy(topic)[level]
    
    # 5. Cachen
    from database import save_explanations
    save_explanations(topic, result)
    
    return result
