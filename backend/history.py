import sqlite3
import json
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "querylens_history.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            db_type TEXT,
            original_query TEXT,
            optimized_sql TEXT,
            score INTEGER,
            safety_status TEXT,
            issues_count INTEGER,
            rows_scanned TEXT,
            full_result TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_to_history(result: dict):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO query_history
        (timestamp, db_type, original_query, optimized_sql, score, safety_status, issues_count, rows_scanned, full_result)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        result.get("db_type", "unknown"),
        result.get("original_query", "")[:500],
        result.get("optimized_sql", "")[:500],
        result.get("score", 0),
        result.get("safety", {}).get("status", "UNKNOWN"),
        len(result.get("issues", [])),
        result.get("rows_scanned", "N/A"),
        json.dumps(result)[:4000],
    ))
    conn.commit()
    conn.close()


def get_history(limit: int = 20) -> list:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, timestamp, db_type, original_query, score, safety_status, issues_count, rows_scanned
        FROM query_history
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
