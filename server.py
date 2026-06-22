"""
Wissens-SRS — Knowledge Spaced Repetition System
Flask Backend mit SQLite, SM-2 Algorithmus, OpenRouter AI
Features: Tags, Language Mode, Random Mode, Library
"""
from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__, static_folder=".")

from database import init_db
init_db()


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


# ═══════════════════════════════════════════════════════════════
# API: Wissens-Erklärungen generieren
# ═══════════════════════════════════════════════════════════════

@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    if len(topic) < 3:
        return jsonify({"error": "Thema muss mindestens 3 Zeichen haben"}), 400
    if len(topic) > 200:
        return jsonify({"error": "Thema darf maximal 200 Zeichen haben"}), 400
    
    from ai import generate_explanations
    result = generate_explanations(topic)
    if result is None:
        return jsonify({"error": "KI konnte keine Erklärungen generieren (API-Key/Netzwerk?)"}), 503
    
    return jsonify({"topic": topic, **result})


@app.route("/api/random", methods=["POST"])
def api_random():
    """Zufälliges Thema aus einer Kategorie."""
    data = request.get_json(silent=True) or {}
    category = (data.get("category") or "").strip()
    if not category:
        return jsonify({"error": "Kategorie ist Pflicht"}), 400
    
    from ai import generate_random
    result = generate_random(category)
    if result is None:
        return jsonify({"error": "KI konnte kein Thema generieren"}), 503
    
    return jsonify(result)


# ═══════════════════════════════════════════════════════════════
# API: Karten (Wissen)
# ═══════════════════════════════════════════════════════════════

@app.route("/api/cards", methods=["GET", "POST"])
def api_cards():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        topic = (data.get("topic") or "").strip()
        explanation = (data.get("explanation") or "").strip()
        level = (data.get("level") or "").strip()
        title = (data.get("title") or topic).strip()
        
        if not all([topic, explanation, level]):
            return jsonify({"error": "topic, explanation und level sind Pflicht"}), 400
        if level not in ("kurz", "kompakt", "ausfuehrlich"):
            return jsonify({"error": "level muss kurz, kompakt oder ausfuehrlich sein"}), 400
        
        from database import create_card
        card = create_card(topic, explanation, level, title)
        return jsonify(card), 201
    
    from database import get_all_cards
    cards = get_all_cards()
    return jsonify(cards)


@app.route("/api/cards/due")
def api_cards_due():
    from database import get_due_cards
    cards = get_due_cards()
    return jsonify(cards)


@app.route("/api/cards/<int:card_id>", methods=["DELETE"])
def api_card_delete(card_id):
    from database import delete_card, get_card
    card = get_card(card_id)
    if not card:
        return jsonify({"error": "Karte nicht gefunden"}), 404
    delete_card(card_id)
    return jsonify({"status": "deleted"})


@app.route("/api/cards/<int:card_id>/review", methods=["POST"])
def api_review(card_id):
    from database import get_card, update_card, add_review
    from srs import sm2
    
    card = get_card(card_id)
    if not card:
        return jsonify({"error": "Karte nicht gefunden"}), 404
    
    data = request.get_json(silent=True) or {}
    rating = data.get("rating")
    if rating is None or not isinstance(rating, int) or rating < 0 or rating > 5:
        return jsonify({"error": "rating muss eine Zahl 0-5 sein"}), 400
    
    updated = sm2(card, rating)
    update_card(card_id,
        ease_factor=updated['ease_factor'],
        interval_days=updated['interval_days'],
        repetitions=updated['repetitions'],
        next_review=updated['next_review'],
        last_reviewed=updated['last_reviewed'],
        review_count=updated['review_count'],
        avg_rating=updated['avg_rating']
    )
    add_review(card_id, rating)
    
    updated['id'] = card_id
    updated['topic'] = card['topic']
    return jsonify(updated)


# ═══════════════════════════════════════════════════════════════
# API: Tags
# ═══════════════════════════════════════════════════════════════

@app.route("/api/tags")
def api_tags():
    from database import get_all_tags
    tags = get_all_tags()
    return jsonify(tags)


@app.route("/api/cards/<int:card_id>/tags", methods=["POST"])
def api_add_tag(card_id):
    data = request.get_json(silent=True) or {}
    tag_name = (data.get("name") or "").strip().lower()
    if not tag_name:
        return jsonify({"error": "Tag-Name ist Pflicht"}), 400
    
    from database import add_tag_to_card
    from database import get_card
    if not get_card(card_id):
        return jsonify({"error": "Karte nicht gefunden"}), 404
    
    result = add_tag_to_card(card_id, tag_name)
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result), 201


@app.route("/api/cards/<int:card_id>/tags/<int:tag_id>", methods=["DELETE"])
def api_remove_tag(card_id, tag_id):
    from database import remove_tag_from_card
    remove_tag_from_card(card_id, tag_id)
    return jsonify({"status": "deleted"})


# ═══════════════════════════════════════════════════════════════
# API: Sprach-Modus
# ═══════════════════════════════════════════════════════════════

@app.route("/api/language/generate", methods=["POST"])
def api_language_generate():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    target_lang = (data.get("target_lang") or "en").strip()
    level = (data.get("level") or "einfach").strip()
    mode = (data.get("mode") or "translate").strip()
    
    if level not in ("einfach", "mittel", "fortgeschritten"):
        return jsonify({"error": "level muss einfach, mittel oder fortgeschritten sein"}), 400
    if mode not in ("translate", "generate"):
        return jsonify({"error": "mode muss translate oder generate sein"}), 400
    if mode == "translate" and not text:
        return jsonify({"error": "text ist bei translate-Modus Pflicht"}), 400
    
    from ai import generate_language
    result = generate_language(text, target_lang, level, mode)
    if result is None:
        return jsonify({"error": "KI konnte keine Übersetzung generieren"}), 503
    
    return jsonify(result)


@app.route("/api/language/cards", methods=["GET", "POST"])
def api_language_cards():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        source_text = (data.get("source_text") or "").strip()
        target_text = (data.get("target_text") or "").strip()
        source_lang = (data.get("source_lang") or "de").strip()
        target_lang = (data.get("target_lang") or "en").strip()
        level = (data.get("level") or "einfach").strip()
        
        if not all([source_text, target_text]):
            return jsonify({"error": "source_text und target_text sind Pflicht"}), 400
        if level not in ("einfach", "mittel", "fortgeschritten"):
            return jsonify({"error": "level muss einfach, mittel oder fortgeschritten sein"}), 400
        
        from database import create_language_card
        card = create_language_card(source_text, target_text, source_lang, target_lang, level)
        return jsonify(card), 201
    
    from database import get_all_language_cards
    cards = get_all_language_cards()
    return jsonify(cards)


@app.route("/api/language/cards/due")
def api_language_due():
    from database import get_due_language_cards
    cards = get_due_language_cards()
    return jsonify(cards)


@app.route("/api/language/cards/<int:card_id>/review", methods=["POST"])
def api_language_review(card_id):
    from database import get_language_card, update_language_card, add_review
    from srs import sm2
    
    card = get_language_card(card_id)
    if not card:
        return jsonify({"error": "Sprachkarte nicht gefunden"}), 404
    
    data = request.get_json(silent=True) or {}
    rating = data.get("rating")
    if rating is None or not isinstance(rating, int) or rating < 0 or rating > 5:
        return jsonify({"error": "rating muss eine Zahl 0-5 sein"}), 400
    
    updated = sm2(card, rating)
    update_language_card(card_id,
        ease_factor=updated['ease_factor'],
        interval_days=updated['interval_days'],
        repetitions=updated['repetitions'],
        next_review=updated['next_review'],
        last_reviewed=updated['last_reviewed'],
        review_count=updated['review_count'],
        avg_rating=updated['avg_rating']
    )
    add_review(card_id, rating, card_type='language')
    
    updated['id'] = card_id
    updated['source_text'] = card['source_text']
    return jsonify(updated)


@app.route("/api/language/cards/<int:card_id>", methods=["DELETE"])
def api_language_delete(card_id):
    from database import delete_language_card, get_language_card
    card = get_language_card(card_id)
    if not card:
        return jsonify({"error": "Sprachkarte nicht gefunden"}), 404
    delete_language_card(card_id)
    return jsonify({"status": "deleted"})


# ═══════════════════════════════════════════════════════════════
# API: Statistiken
# ═══════════════════════════════════════════════════════════════

@app.route("/api/stats")
def api_stats():
    from database import get_stats
    return jsonify(get_stats())


# ── Main ────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("TOOL_PORT", "5111"))
    os.makedirs("data", exist_ok=True)
    app.run(host="0.0.0.0", port=port, debug=False)
