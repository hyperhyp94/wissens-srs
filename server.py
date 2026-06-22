from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__, static_folder=".")

# ── Datenbank-Pfad ──────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "wissens.db")

# ── Routes ──────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/api/generate", methods=["POST"])
def api_generate():
    """KI-Erklärungen für ein Thema generieren."""
    return jsonify({"status": "not implemented"}), 501

@app.route("/api/explanations/<topic>")
def api_explanations(topic):
    return jsonify({"status": "not implemented"}), 501

@app.route("/api/cards", methods=["GET", "POST"])
def api_cards():
    if request.method == "POST":
        return jsonify({"status": "not implemented"}), 501
    return jsonify({"status": "not implemented"}), 501

@app.route("/api/cards/due")
def api_cards_due():
    return jsonify({"status": "not implemented"}), 501

@app.route("/api/cards/<int:card_id>/review", methods=["POST"])
def api_review(card_id):
    return jsonify({"status": "not implemented"}), 501

@app.route("/api/stats")
def api_stats():
    return jsonify({"status": "not implemented"}), 501

# ── Main ────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("TOOL_PORT", "5111"))
    os.makedirs("data", exist_ok=True)
    app.run(host="0.0.0.0", port=port, debug=False)
