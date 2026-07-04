#!/usr/bin/env python3
"""Migration: rebuild history.db with the normalized schema.

Drops the response column, deduplicates model/error/prompt text into lookup
tables, removes orphaned model_results, and VACUUMs the file.
Run from the repo root: python3 scripts/migrate_normalized.py
"""

import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_utils import HISTORY_DB, init_schema  # noqa: E402


def migrate(db_path: Path = HISTORY_DB) -> int:
    if not db_path.exists():
        print(f"Error: {db_path} not found", file=sys.stderr)
        return 1

    old_size = db_path.stat().st_size
    print(f"Migrating {db_path} ({old_size // 1024} KB) …")

    tmp_path = db_path.with_suffix(".db.tmp")
    if tmp_path.exists():
        tmp_path.unlink()

    src = sqlite3.connect(str(db_path))
    src.execute("PRAGMA foreign_keys = OFF")
    dst = sqlite3.connect(str(tmp_path))
    init_schema(dst)

    # Populate lookup tables
    for (text,) in src.execute("SELECT DISTINCT prompt FROM runs WHERE prompt IS NOT NULL"):
        dst.execute("INSERT INTO prompts (text) VALUES (?)", (text,))

    for (name,) in src.execute("SELECT DISTINCT model FROM model_results WHERE model IS NOT NULL"):
        dst.execute("INSERT OR IGNORE INTO models (name) VALUES (?)", (name,))
    for (name,) in src.execute(
        "SELECT DISTINCT fastest_model FROM runs WHERE fastest_model IS NOT NULL AND fastest_model != ''"
    ):
        dst.execute("INSERT OR IGNORE INTO models (name) VALUES (?)", (name,))

    for (text,) in src.execute("SELECT DISTINCT error FROM model_results WHERE error IS NOT NULL"):
        dst.execute("INSERT INTO errors (text) VALUES (?)", (text,))

    # Copy runs (only those that still exist — pruned run IDs are skipped)
    for r_id, ts, prompt, fm, ft in src.execute(
        "SELECT id, timestamp, prompt, fastest_model, fastest_time FROM runs ORDER BY id"
    ):
        p_id = dst.execute("SELECT id FROM prompts WHERE text=?", (prompt,)).fetchone()
        p_id = p_id[0] if p_id else None
        fm_id = None
        if fm:
            row = dst.execute("SELECT id FROM models WHERE name=?", (fm,)).fetchone()
            fm_id = row[0] if row else None
        dst.execute(
            "INSERT INTO runs (id, timestamp, prompt_id, fastest_model_id, fastest_time) VALUES (?,?,?,?,?)",
            (r_id, ts, p_id, fm_id, ft),
        )

    # Copy model_results (only for runs that exist — orphans are dropped)
    for run_id, model, success, error, rt, tg, tt in src.execute(
        "SELECT run_id, model, success, error, response_time, tokens_generated, total_tokens "
        "FROM model_results WHERE run_id IN (SELECT id FROM runs)"
    ):
        m_id = dst.execute("SELECT id FROM models WHERE name=?", (model,)).fetchone()[0]
        e_id = None
        if error:
            row = dst.execute("SELECT id FROM errors WHERE text=?", (error,)).fetchone()
            e_id = row[0] if row else None
        dst.execute(
            "INSERT INTO model_results "
            "(run_id, model_id, success, error_id, response_time, tokens_generated, total_tokens) "
            "VALUES (?,?,?,?,?,?,?)",
            (run_id, m_id, success, e_id, rt, tg, tt),
        )

    dst.commit()
    dst.execute("VACUUM")
    run_count = dst.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    result_count = dst.execute("SELECT COUNT(*) FROM model_results").fetchone()[0]
    dst.close()
    src.close()

    # Replace old DB
    db_path.unlink()
    tmp_path.rename(db_path)

    new_size = db_path.stat().st_size
    print("Done: Migration complete")
    print(f"  {run_count} runs · {result_count} model results")
    print(f"  Size: {old_size // 1024} KB -> {new_size // 1024} KB ({(1 - new_size / old_size) * 100:.0f}% smaller)")
    return 0


if __name__ == "__main__":
    raise SystemExit(migrate())
