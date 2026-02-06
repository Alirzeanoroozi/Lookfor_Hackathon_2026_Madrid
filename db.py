from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path("lookfor.db")  # this file will be created in your project folder


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # optional: makes rows dict-like
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            name TEXT
        );
        """
    )

    # Email support session tables
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS email_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_email TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            shopify_customer_id TEXT NOT NULL,
            escalated INTEGER DEFAULT 0,
            escalated_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS session_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            sender TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES email_sessions(id)
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tool_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            message_id INTEGER,
            tool_name TEXT NOT NULL,
            tool_input TEXT,
            tool_output TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES email_sessions(id)
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS escalations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            summary_json TEXT NOT NULL,
            reason TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES email_sessions(id)
        );
        """
    )

    conn.commit()
    conn.close()


def insert_user(email: str, name: str = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (email, name) VALUES (?, ?);",
        (email, name),
    )
    conn.commit()
    conn.close()


def list_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, email, name FROM users;")
    rows = cur.fetchall()
    conn.close()
    return rows


# --- Email session APIs ---


def create_session(
    customer_email: str,
    first_name: str,
    last_name: str,
    shopify_customer_id: str,
) -> int:
    """Create a new email session. Returns session id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO email_sessions (customer_email, first_name, last_name, shopify_customer_id)
           VALUES (?, ?, ?, ?);""",
        (customer_email, first_name, last_name, shopify_customer_id),
    )
    session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return session_id or 0


def get_session(session_id: int) -> dict[str, Any]:
    """Get session by id. Returns dict or None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM email_sessions WHERE id = ?;", (session_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def is_session_escalated(session_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT escalated FROM email_sessions WHERE id = ?;", (session_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row and row["escalated"])


def mark_session_escalated(session_id: int) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE email_sessions SET escalated = 1, escalated_at = datetime('now') WHERE id = ?;",
        (session_id,),
    )
    conn.commit()
    conn.close()


def add_message(
    session_id: int,
    role: str,
    content: str,
    sender: str | None = None,
) -> int:
    """Add a message to the session. Returns message id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO session_messages (session_id, role, content, sender) VALUES (?, ?, ?, ?);",
        (session_id, role, content, sender or role),
    )
    msg_id = cur.lastrowid
    conn.commit()
    conn.close()
    return msg_id or 0


def get_session_messages(session_id: int) -> list[dict[str, Any]]:
    """Get all messages for a session in order."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, role, content, sender FROM session_messages WHERE session_id = ? ORDER BY id;",
        (session_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_tool_call(
    session_id: int,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_output: dict[str, Any],
    message_id: int | None = None,
) -> int:
    """Record a tool call. Returns tool_call id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO tool_calls (session_id, message_id, tool_name, tool_input, tool_output)
           VALUES (?, ?, ?, ?, ?);""",
        (session_id, message_id, tool_name, json.dumps(tool_input), json.dumps(tool_output)),
    )
    tc_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tc_id or 0


def get_session_tool_calls(session_id: int) -> list[dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, tool_name, tool_input, tool_output FROM tool_calls WHERE session_id = ? ORDER BY id;",
        (session_id,),
    )
    rows = cur.fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["tool_input"] = json.loads(d["tool_input"] or "{}")
        except json.JSONDecodeError:
            pass
        try:
            d["tool_output"] = json.loads(d["tool_output"] or "{}")
        except json.JSONDecodeError:
            pass
        out.append(d)
    return out


def add_escalation(
    session_id: int,
    summary_json: dict[str, Any],
    reason: str | None = None,
) -> int:
    """Record an escalation. Returns escalation id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO escalations (session_id, summary_json, reason) VALUES (?, ?, ?);",
        (session_id, json.dumps(summary_json), reason),
    )
    eid = cur.lastrowid
    conn.commit()
    conn.close()
    return eid or 0


if __name__ == "__main__":
    # 1) Create DB and table
    init_db()

    # 2) Insert a sample user (ignore error if already exists)
    try:
        insert_user("test@example.com", "Test User")
    except sqlite3.IntegrityError:
        pass

    # 3) Read back and print
    for row in list_users():
        print(dict(row))