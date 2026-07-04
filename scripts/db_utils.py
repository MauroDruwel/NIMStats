"""Shared SQLite utilities for reading/writing benchmark history."""

import sqlite3
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
HISTORY_DB = REPO_ROOT / "history.db"
MAX_RUNS = 720


def init_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS prompts (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS models (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS errors (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT UNIQUE
        );
        CREATE TABLE IF NOT EXISTS runs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp        TEXT    NOT NULL,
            prompt_id        INTEGER NOT NULL REFERENCES prompts(id),
            fastest_model_id INTEGER          REFERENCES models(id),
            fastest_time     INTEGER
        );
        CREATE TABLE IF NOT EXISTS model_results (
            run_id           INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
            model_id         INTEGER NOT NULL REFERENCES models(id),
            success          INTEGER NOT NULL DEFAULT 0,
            error_id         INTEGER          REFERENCES errors(id),
            response_time    INTEGER,
            tokens_generated INTEGER,
            total_tokens     INTEGER,
            PRIMARY KEY (run_id, model_id)
        );
        CREATE INDEX IF NOT EXISTS idx_runs_ts  ON runs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_mr_model ON model_results(model_id);
    """)


def _get_or_create(conn: sqlite3.Connection, table: str, col: str, value: Any) -> int | None:
    if not value:
        return None
    row = conn.execute(f"SELECT id FROM {table} WHERE {col} = ?", (value,)).fetchone()
    if row:
        return row[0]
    cur = conn.execute(f"INSERT INTO {table} ({col}) VALUES (?)", (value,))
    return cur.lastrowid


def write_run(run: dict[str, Any], db_path: Path = HISTORY_DB) -> None:
    """Insert a benchmark run into the database and prune runs beyond MAX_RUNS."""
    summary = run.get("summary", {})
    conn = sqlite3.connect(str(db_path))
    try:
        init_schema(conn)
        prompt_id = _get_or_create(conn, "prompts", "text", run.get("prompt"))
        fastest_model_id = _get_or_create(conn, "models", "name", summary.get("fastestModel"))

        cur = conn.execute(
            """INSERT INTO runs (timestamp, prompt_id, fastest_model_id, fastest_time)
               VALUES (?, ?, ?, ?)""",
            (run.get("timestamp"), prompt_id, fastest_model_id, summary.get("fastestTime")),
        )
        run_id = cur.lastrowid

        for m in run.get("models", []):
            model_id = _get_or_create(conn, "models", "name", m.get("model"))
            error_id = _get_or_create(conn, "errors", "text", m.get("error"))
            conn.execute(
                """INSERT INTO model_results
                   (run_id, model_id, success, error_id, response_time, tokens_generated, total_tokens)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    model_id,
                    1 if m.get("success") else 0,
                    error_id,
                    m.get("responseTime"),
                    m.get("tokensGenerated"),
                    m.get("totalTokens"),
                ),
            )

        conn.execute(
            f"DELETE FROM runs WHERE id NOT IN "
            f"(SELECT id FROM runs ORDER BY timestamp DESC LIMIT {MAX_RUNS})"
        )
        conn.commit()
    finally:
        conn.close()
