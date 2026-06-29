from flask import Flask, jsonify, request
from uuid import uuid4

from db import init_db, save_content_decision, write_audit_log, get_recent_logs
from detector import classify_with_groq, combine_signal_scores
from stylometry import analyze_stylometry
from labels import get_transparency_label

app = Flask(__name__)

init_db()


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Provenance Guard API is running",
        "status": "ok"
    })


@app.route("/submit", methods=["POST"])
def submit_content():
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body must be valid JSON."
        }), 400

    creator_id = data.get("creator_id")
    text = data.get("text") or data.get("content")
    title = data.get("title", "Untitled")

    if not creator_id:
        return jsonify({
            "error": "Missing required field: creator_id"
        }), 400

    if not text:
        return jsonify({
            "error": "Missing required field: text"
        }), 400

    content_id = str(uuid4())

    llm_signal = classify_with_groq(text)
    stylometric_signal = analyze_stylometry(text)
    scoring = combine_signal_scores(llm_signal, stylometric_signal)

    attribution = scoring["attribution"]
    confidence = scoring["confidence"]
    label = get_transparency_label(attribution)

    signal_data = {
        "llm_signal": llm_signal,
        "stylometric_signal": stylometric_signal,
        "combined_scoring": scoring
    }

    save_content_decision(
        content_id=content_id,
        creator_id=creator_id,
        title=title,
        content=text,
        attribution=attribution,
        confidence=confidence,
        label=label,
        signal_data=signal_data,
        status="classified",
    )

    audit_entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "attribution": attribution,
        "confidence": confidence,
        "llm_score": scoring["llm_score"],
        "stylometric_score": scoring["stylometric_score"],
        "llm_classification": llm_signal["classification"],
        "stylometric_classification": stylometric_signal["classification"],
        "weights": scoring["weights"],
        "status": "classified"
    }

    write_audit_log(
        event_type="classification",
        content_id=content_id,
        event_data=audit_entry,
    )

    return jsonify({
        "content_id": content_id,
        "creator_id": creator_id,
        "title": title,
        "attribution": attribution,
        "confidence": confidence,
        "label": label,
        "signals": signal_data,
        "status": "classified"
    }), 201


@app.route("/log", methods=["GET"])
def view_log():
    entries = get_recent_logs()
    return jsonify({
        "entries": entries
    })


if __name__ == "__main__":
    app.run(debug=True)