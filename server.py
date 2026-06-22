"""
Wissens-SRS — Knowledge Spaced Repetition System
Flask Backend mit SQLite, SM-2 Algorithmus, OpenRouter AI
"""
from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__, static_folder=".")

# ── Datenbank beim Start initialisieren ─────────────────────────
from database import init_db, get_db
init_db()

# ── Routes ──────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


# ═══════════════════════════════════════════════════════════════
# API: Erklärungen generieren
# ═══════════════════════════════════════════════════════════════

@app.route("/api/generate", methods=["POST"])
def api_generate():
    """KI-Erklärungen für ein Thema generieren (mit Cache)."""
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    
    if len(topic) < 3:
        return jsonify({"error": "Thema muss mindestens 3 Zeichen haben"}), 400
    
    from ai import generate_explanations
    result = generate_explanations(topic)
    
    if result is None:
        return jsonify({"error": "Konnte keine Erklärungen generieren"}), 500
    
    return jsonify({"topic": topic, "explanations": result})


@app.route("/api/explanations/<path:topic>")
def api_explanations(topic):
    """Gespeicherte Erklärungen abrufen."""
    from database import get_explanations
    result = get_explanations(topic)
    if not result:
        return jsonify({"error": "Keine Erklärungen gefunden"}), 404
    return jsonify({"topic": topic, "explanations": result})


# ═══════════════════════════════════════════════════════════════
# API: Karten
# ═══════════════════════════════════════════════════════════════

@app.route("/api/cards", methods=["GET", "POST"])
def api_cards():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        topic = (data.get("topic") or "").strip()
        explanation = (data.get("explanation") or "").strip()
        level = (data.get("level") or "").strip()
        
        if not all([topic, explanation, level]):
            return jsonify({"error": "topic, explanation und level sind Pflicht"}), 400
        
        if level not in ("easy", "abitur", "professor"):
            return jsonify({"error": "level muss easy, abitur oder professor sein"}), 400
        
        from database import create_card
        card = create_card(topic, explanation, level)
        return jsonify(card), 201
    
    # GET: Alle Karten
    from database import get_all_cards
    cards = get_all_cards()
    return jsonify(cards)


@app.route("/api/cards/due")
def api_cards_due():
    """Heute fällige Karten."""
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
    """Karte reviewen mit SM-2 Bewertung."""
    from database import get_card, update_card, add_review
    from srs import sm2
    
    card = get_card(card_id)
    if not card:
        return jsonify({"error": "Karte nicht gefunden"}), 404
    
    data = request.get_json(silent=True) or {}
    rating = data.get("rating")
    
    if rating is None or not isinstance(rating, int) or rating < 0 or rating > 5:
        return jsonify({"error": "rating muss eine Zahl 0-5 sein"}), 400
    
    # SM-2 anwenden
    updated = sm2(card, rating)
    
    # In DB speichern
    update_card(card_id,
        ease_factor=updated['ease_factor'],
        interval_days=updated['interval_days'],
        repetitions=updated['repetitions'],
        next_review=updated['next_review'],
        last_reviewed=updated['last_reviewed'],
        review_count=updated['review_count'],
        avg_rating=updated['avg_rating']
    )
    
    # Review loggen
    add_review(card_id, rating)
    
    updated['id'] = card_id
    updated['topic'] = card['topic']
    return jsonify(updated)


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
