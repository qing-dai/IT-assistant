import sqlite3
from pathlib import Path


DB_PATH = Path("triage_results_new.db")


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
        freshness_score REAL NOT NULL,
        predicted_category TEXT NOT NULL,
        rank_score REAL NOT NULL,

        fused_score REAL NOT NULL,
        decision_source TEXT NOT NULL,
        llm_reason TEXT,
        llm_relevance_score REAL NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def get_existing_ids() -> set[str]:
    """Return the set of all article_ids already stored (any run, any keep value)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT article_id FROM triage_results")
    ids = {row[0] for row in cursor.fetchall()}
    conn.close()
    return ids


def get_latest_run_items(limit: int = 90) -> list[dict]:
    """Return the most recently ingested articles (kept + discarded), sorted by fused_score DESC."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM (
            SELECT * FROM triage_results ORDER BY id DESC LIMIT ?
        )
        ORDER BY fused_score DESC
    """, (limit,))
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    return [dict(zip(columns, row)) for row in rows]


def get_filtered_items() -> list[dict]:
    """Return kept articles, one row per article_id (latest run wins), sorted by rank."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*
        FROM triage_results t
        INNER JOIN (
            SELECT article_id, MAX(id) AS max_id
            FROM triage_results
            WHERE keep = 1
            GROUP BY article_id
        ) latest ON t.id = latest.max_id
        ORDER BY t.rank_score DESC, t.published_at DESC, t.article_id ASC
    """)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    return [dict(zip(columns, row)) for row in rows]


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
        freshness_score,
        predicted_category,
        rank_score,
        fused_score,
        decision_source,
        llm_reason,
        llm_relevance_score
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        result.freshness_score,
        result.predicted_category,
        result.rank_score,
        result.fused_score,
        result.decision_source,
        result.llm_reason,
        result.llm_relevance_score,
    ))

    conn.commit()
    conn.close()
