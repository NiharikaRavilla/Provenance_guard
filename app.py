from flask import Flask, jsonify, request
from uuid import uuid4

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from db import (
    init_db,
    save_content_decision,
    get_content_decision,
    update_content_status,
    save_appeal,
    write_audit_log,
    get_recent_logs,
)
from detector import classify_with_groq, combine_signal_scores
from stylometry import analyze_stylometry
from labels import get_transparency_label

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

init_db()


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Provenance Guard API is running",
        "status": "ok"
    })


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
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
        "event": "classification decision created",
        "attribution": attribution,
        "confidence": confidence,
        "label": label,
        "llm_score": scoring["llm_score"],
        "stylometric_score": scoring["stylometric_score"],
        "llm_classification": llm_signal["classification"],
        "stylometric_classification": stylometric_signal["classification"],
        "signals_used": ["llm_signal", "stylometric_signal"],
        "weights": scoring["weights"],
        "appeal_filed": False,
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


@app.route("/appeal", methods=["POST"])
def submit_appeal():
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body must be valid JSON."
        }), 400

    content_id = data.get("content_id")
    creator_id = data.get("creator_id")
    creator_reasoning = data.get("creator_reasoning") or data.get("reason")

    if not content_id:
        return jsonify({
            "error": "Missing required field: content_id"
        }), 400

    if not creator_reasoning:
        return jsonify({
            "error": "Missing required field: creator_reasoning"
        }), 400

    original_decision = get_content_decision(content_id)

    if original_decision is None:
        return jsonify({
            "error": "No content decision found for that content_id."
        }), 404

    previous_status = original_decision["status"]
    new_status = "under_review"

    appeal_id = save_appeal(
        content_id=content_id,
        creator_id=creator_id,
        creator_reasoning=creator_reasoning,
        status=new_status,
    )

    update_content_status(content_id, new_status)

    audit_entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "appeal_id": appeal_id,
        "event": "creator appeal submitted",
        "appeal_reasoning": creator_reasoning,
        "original_attribution": original_decision["attribution"],
        "original_confidence": original_decision["confidence"],
        "original_label": original_decision["label"],
        "original_signals": original_decision["signals"],
        "previous_status": previous_status,
        "status": new_status,
        "appeal_filed": True
    }

    write_audit_log(
        event_type="appeal",
        content_id=content_id,
        event_data=audit_entry,
    )

    return jsonify({
        "appeal_id": appeal_id,
        "content_id": content_id,
        "status": new_status,
        "message": "Appeal submitted successfully. The content status has been updated to under_review."
    }), 201


@app.route("/log", methods=["GET"])
def view_log():
    entries = get_recent_logs()
    return jsonify({
        "entries": entries
    })


if __name__ == "__main__":
    app.run(debug=True)