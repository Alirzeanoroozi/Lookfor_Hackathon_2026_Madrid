import sqlite3
from pathlib import Path

DB_PATH = Path("lookfor.db")  # this file will be created in your project folder


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # optional: makes rows dict-like
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Create a sample table if it doesn't exist
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            name TEXT
        );
        """
    )

    conn.commit()
    conn.close()


def insert_user(email: str, name: str | None = None):
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