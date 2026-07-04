#!/usr/bin/env python3
"""One-time migration: history.json → history.db.

Removes defunct models listed in REMOVED_MODELS during import.
Run from the repo root: python3 scripts/migrate_to_sqlite.py
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_utils import HISTORY_DB, init_schema, _get_or_create  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
HISTORY_JSON = REPO_ROOT / "history.json"

# Models that have been removed/renamed and should not appear in the new DB
REMOVED_MODELS: set[str] = {"moonshotai/kimi-k2.5"}


def main() -> int:
    if not HISTORY_JSON.exists():
        print(f"Error: {HISTORY_JSON} not found", file=sys.stderr)
        return 1

    print(f"Reading {HISTORY_JSON} …")
    history = json.loads(HISTORY_JSON.read_text(encoding="utf-8"))
    runs: list[dict] = history.get("runs", [])
    print(f"  {len(runs)} runs found")
    print(f"  Removing defunct models: {', '.join(REMOVED_MODELS)}")

    if HISTORY_DB.exists():
        print(f"Removing existing {HISTORY_DB} …")
        HISTORY_DB.unlink()

    conn = sqlite3.connect(str(HISTORY_DB))
    init_schema(conn)

    removed_entries = 0
    for run in reversed(runs):  # insert oldest-first so AUTO IDs are chronological
        models = [m for m in run.get("models", []) if m.get("model") not in REMOVED_MODELS]
        removed_entries += len(run.get("models", [])) - len(models)

        summary = run.get("summary", {})
        fastest_model = summary.get("fastestModel")
        fastest_time = summary.get("fastestTime", 0) or 0
        if fastest_model in REMOVED_MODELS:
            successful = [m for m in models if m.get("success")]
            if successful:
                fastest = min(successful, key=lambda x: x.get("responseTime") or float("inf"))
                fastest_model = fastest.get("model", "N/A")
                fastest_time = fastest.get("responseTime", 0) or 0
            else:
                fastest_model = "N/A"
                fastest_time = 0

        prompt_id = _get_or_create(conn, "prompts", "text", run.get("prompt"))
        fastest_model_id = _get_or_create(conn, "models", "name", fastest_model) if fastest_model and fastest_model != "N/A" else None

        cur = conn.execute(
            """INSERT INTO runs (timestamp, prompt_id, fastest_model_id, fastest_time)
               VALUES (?, ?, ?, ?)""",
            (run.get("timestamp"), prompt_id, fastest_model_id, fastest_time),
        )
        run_id = cur.lastrowid

        for m in models:
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

    conn.execute("VACUUM")
    conn.commit()

    run_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    result_count = conn.execute("SELECT COUNT(*) FROM model_results").fetchone()[0]
    conn.close()

    db_kb = HISTORY_DB.stat().st_size // 1024
    json_kb = HISTORY_JSON.stat().st_size // 1024
    print(f"✓ Created {HISTORY_DB}")
    print(f"  {run_count} runs · {result_count} model results")
    if removed_entries:
        print(f"  Removed {removed_entries} defunct model entries")
    print(f"  DB size: {db_kb} KB  (was {json_kb} KB JSON)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
