"""
KI-Erklärungsgenerierung via OpenRouter API.
Generiert 3 Erklärungsstufen: easy (Kinderleicht), abitur, professor.
"""
import json
import os
import urllib.request
import urllib.error

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")


def _call_openrouter(topic):
    """OpenRouter API aufrufen, Erklärungen generieren."""
    if not OPENROUTER_KEY:
        return None
    
    prompt = f"""Du bist ein Wissensvermittler. Erkläre das folgende Thema auf drei verschiedenen Niveaustufen.
Antworte NUR mit einem gültigen JSON-Objekt (kein Markdown, kein Code-Block):

{{
  "easy": "Erklärung für ein 8-jähriges Kind. Einfache Worte, bildhaft, kurz (2-3 Sätze).",
  "abitur": "Erklärung auf Abitur-Niveau. Fachbegriffe erklärt, logischer Aufbau (4-6 Sätze).",
  "professor": "Erklärung auf Universitäts-Niveau. Wissenschaftlich präzise, mit Fachterminologie (6-10 Sätze)."
}}

Thema: {topic}"""

    payload = json.dumps({
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Du bist ein Wissensvermittler. Antworte NUR mit JSON, kein Markdown."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1024,
        "temperature": 0.7
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
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"]
            # Clean up: remove markdown code blocks if present
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            return json.loads(content)
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"[ai] OpenRouter error: {e}")
        return None


def _generate_dummy(topic):
    """Fallback: Dummy-Erklärungen wenn kein API-Key oder API nicht erreichbar."""
    return {
        "easy": f"Stell dir vor, {topic.lower()} – das ist ganz einfach! Es passiert einfach so in der Natur und du kannst es jeden Tag sehen. Cool, oder?",
        "abitur": f"Das Thema '{topic}' lässt sich auf Abitur-Niveau wie folgt erklären: Es handelt sich um einen Prozess, bei dem mehrere Faktoren zusammenspielen. Die grundlegenden Mechanismen sind wissenschaftlich gut dokumentiert und basieren auf physikalischen Prinzipien.",
        "professor": f"Eine wissenschaftlich präzise Betrachtung des Themas '{topic}' erfordert die Analyse der zugrundeliegenden Mechanismen. Ausgehend von den etablierten Theorien (vgl. Standardliteratur) manifestiert sich das Phänomen als Emergenz komplexer Wechselwirkungen auf mikro- und makroskopischer Ebene. Die aktuelle Forschung deutet auf eine multifaktorielle Genese hin."
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
    
    # 3. Fallback: Dummy
    if result is None or not isinstance(result, dict):
        result = _generate_dummy(topic)
    
    # 4. Validieren: alle 3 Level müssen vorhanden sein
    for level in ['easy', 'abitur', 'professor']:
        if level not in result or not result[level]:
            result[level] = _generate_dummy(topic)[level]
    
    # 5. Cachen
    from database import save_explanations
    save_explanations(topic, result)
    
    return result
