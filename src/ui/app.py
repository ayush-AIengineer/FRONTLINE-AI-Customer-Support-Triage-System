"""
FRONTLINE — Web Dashboard (Level 3 UI)
Flask app serving a live dashboard of triage results.

Run with:  python src/ui/app.py
Then open: http://localhost:5000
"""

import json
import sys
import os
from pathlib import Path
from flask import Flask, render_template, jsonify, request

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

app = Flask(__name__, template_folder="templates", static_folder="static")

OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs"


def get_latest_results() -> list[dict]:
    """Load the most recent triage results file."""
    files = sorted(OUTPUTS_DIR.glob("triage_results_*.json"), reverse=True)
    if not files:
        return []
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/results")
def api_results():
    results = get_latest_results()
    return jsonify(results)


@app.route("/api/stats")
def api_stats():
    results = get_latest_results()
    if not results:
        return jsonify({})

    total = len(results)
    stats = {
        "total": total,
        "needs_human": sum(1 for r in results if r.get("needs_human")),
        "by_priority": {},
        "by_category": {},
        "adversarial_count": sum(1 for r in results if r.get("category") == "adversarial"),
        "avg_confidence": round(
            sum(r.get("confidence", 0) for r in results) / total, 3
        ),
    }

    for r in results:
        p = r.get("priority", "P3")
        stats["by_priority"][p] = stats["by_priority"].get(p, 0) + 1
        c = r.get("category", "unclear")
        stats["by_category"][c] = stats["by_category"].get(c, 0) + 1

    return jsonify(stats)


@app.route("/api/triage", methods=["POST"])
def api_triage_single():
    """Live triage endpoint for the dashboard."""
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "No message provided"}), 400

    try:
        from src.triage.processor import process_single
        result = process_single(message)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("Starting FRONTLINE Dashboard at http://localhost:5000")
    app.run(debug=True, port=5000)
