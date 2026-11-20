#!/usr/bin/env python3
"""Export history.db to a SQL file compatible with Cloudflare D1."""

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HISTORY_DB = REPO_ROOT / "history.db"
OUTPUT_SQL = REPO_ROOT / "scripts" / "d1_seed.sql"


def escape_str(val: str | None) -> str:
    if val is None:
        return "NULL"
    return "'" + val.replace("'", "''") + "'"


def escape_val(val) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    return escape_str(str(val))


def main() -> int:
    if not HISTORY_DB.exists():
        print(f"Error: {HISTORY_DB} not found", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(HISTORY_DB))
    try:
        out_lines = [
            "-- Cloudflare D1 Seed Script generated from history.db",
            "PRAGMA foreign_keys = OFF;",
            "",
        ]

        # 1. Prompts
        prompts = conn.execute("SELECT id, text FROM prompts ORDER BY id").fetchall()
        print(f"Exporting {len(prompts)} prompts...")
        for pid, text in prompts:
            out_lines.append(f"INSERT OR IGNORE INTO prompts (id, text) VALUES ({pid}, {escape_str(text)});")

        # 2. Models
        models = conn.execute("SELECT id, name, intelligence_score FROM models ORDER BY id").fetchall()
        print(f"Exporting {len(models)} models...")
        for mid, name, intel in models:
            out_lines.append(f"INSERT OR IGNORE INTO models (id, name, intelligence_score) VALUES ({mid}, {escape_str(name)}, {escape_val(intel)});")

        # 3. Errors
        errors = conn.execute("SELECT id, text FROM errors ORDER BY id").fetchall()
        print(f"Exporting {len(errors)} errors...")
        for eid, text in errors:
            out_lines.append(f"INSERT OR IGNORE INTO errors (id, text) VALUES ({eid}, {escape_str(text)});")

        # 4. Runs (retain trailing 30 days / max 1000 runs to keep D1 seed lean and fast)
        runs = conn.execute(
            "SELECT id, timestamp, prompt_id, fastest_model_id, fastest_time "
            "FROM runs ORDER BY id DESC LIMIT 1000"
        ).fetchall()
        runs.reverse()
        print(f"Exporting {len(runs)} recent runs...")
        run_ids = set()
        for rid, ts, pid, fmid, ft in runs:
            run_ids.add(rid)
            out_lines.append(
                f"INSERT OR IGNORE INTO runs (id, timestamp, prompt_id, fastest_model_id, fastest_time) "
                f"VALUES ({rid}, {escape_str(ts)}, {pid}, {escape_val(fmid)}, {escape_val(ft)});"
            )

        # 5. Model Results
        if run_ids:
            min_rid = min(run_ids)
            max_rid = max(run_ids)
            results = conn.execute(
                f"SELECT run_id, model_id, success, error_id, response_time, tokens_generated, total_tokens, time_to_first_token "
                f"FROM model_results WHERE run_id BETWEEN {min_rid} AND {max_rid} ORDER BY run_id"
            ).fetchall()
            print(f"Exporting {len(results)} model results...")
            for rid, mid, succ, eid, rt, tg, tt, ttft in results:
                out_lines.append(
                    f"INSERT OR IGNORE INTO model_results (run_id, model_id, success, error_id, response_time, tokens_generated, total_tokens, time_to_first_token) "
                    f"VALUES ({rid}, {mid}, {succ}, {escape_val(eid)}, {escape_val(rt)}, {escape_val(tg)}, {escape_val(tt)}, {escape_val(ttft)});"
                )

        out_lines.append("")
        out_lines.append("PRAGMA foreign_keys = ON;")

        OUTPUT_SQL.write_text("\n".join(out_lines), encoding="utf-8")
        print(f"✓ Wrote {len(out_lines)} SQL statements to {OUTPUT_SQL} ({OUTPUT_SQL.stat().st_size // 1024} KB)")

    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
