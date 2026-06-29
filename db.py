import sqlite3
import json
from datetime import datetime, timezone

DB_NAME = "provenance_guard.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS content_decisions (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            attribution TEXT NOT NULL,
            confidence REAL NOT NULL,
            label TEXT NOT NULL,
            signal_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            content_id TEXT NOT NULL,
            event_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def save_content_decision(
    content_id,
    creator_id,
    title,
    content,
    attribution,
    confidence,
    label,
    signal_data,
    status="classified",
):
    created_at = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO content_decisions (
            id,
            creator_id,
            title,
            content,
            attribution,
            confidence,
            label,
            signal_json,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            content_id,
            creator_id,
            title,
            content,
            attribution,
            confidence,
            label,
            json.dumps(signal_data),
            status,
            created_at,
        ),
    )

    conn.commit()
    conn.close()


def write_audit_log(event_type, content_id, event_data):
    created_at = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO audit_log (
            event_type,
            content_id,
            event_json,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            event_type,
            content_id,
            json.dumps(event_data),
            created_at,
        ),
    )

    conn.commit()
    conn.close()


def get_recent_logs(limit=20):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT event_type, content_id, event_json, created_at
        FROM audit_log
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )

    rows = cursor.fetchall()
    conn.close()

    entries = []

    for row in rows:
        event_data = json.loads(row["event_json"])
        event_data["event_type"] = row["event_type"]
        event_data["content_id"] = row["content_id"]
        event_data["timestamp"] = row["created_at"]
        entries.append(event_data)

    return entries