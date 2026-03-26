import sqlite3
from pathlib import Path


DB_PATH = Path("triage_results.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS triage_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        run_id TEXT NOT NULL,
        article_id TEXT NOT NULL,
        source TEXT NOT NULL,
        title TEXT NOT NULL,
        body TEXT,
        published_at TEXT NOT NULL,
        retrieved_at TEXT NOT NULL,

        keep INTEGER NOT NULL,
        final_score REAL NOT NULL,
        lexical_score REAL NOT NULL,
        semantic_score REAL NOT NULL,
        severity_score REAL NOT NULL,
        entity_score REAL NOT NULL,
        freshness_score REAL NOT NULL,
        predicted_category TEXT NOT NULL,
        rank_score REAL NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def insert_triage_result(result, run_id: str, retrieved_at: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO triage_results (
        run_id,
        article_id,
        source,
        title,
        body,
        published_at,
        retrieved_at,
        keep,
        final_score,
        lexical_score,
        semantic_score,
        severity_score,
        entity_score,
        freshness_score,
        predicted_category,
        rank_score
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        result.id,
        result.source,
        result.title,
        result.body,
        result.published_at.isoformat(),
        retrieved_at,
        int(result.keep),
        result.final_score,
        result.lexical_score,
        result.semantic_score,
        result.severity_score,
        result.entity_score,
        result.freshness_score,
        result.predicted_category,
        result.rank_score,
    ))

    conn.commit()
    conn.close()
