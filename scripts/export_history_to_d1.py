"""Export a SQLite snapshot for a new D1 database or a timestamped backfill."""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HISTORY_DB = REPO_ROOT / "history.db"
OUTPUT_SQL = REPO_ROOT / "scripts" / "d1_seed.sql"
BACKFILL_SQL = REPO_ROOT / "scripts" / "d1_backfill.sql"


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


def write_backfill(conn: sqlite3.Connection, output: Path, after: str) -> None:
    runs = conn.execute("""
        SELECT r.id, r.timestamp, p.text, m.name, r.fastest_time
        FROM runs r
        JOIN prompts p ON p.id = r.prompt_id
        LEFT JOIN models m ON m.id = r.fastest_model_id
        WHERE r.timestamp > ?
        ORDER BY r.timestamp, r.id
    """, (after,)).fetchall()
    conn.row_factory = sqlite3.Row
    count = 0
    with output.open("w", encoding="utf-8") as sql:
        print("-- Requires scripts/d1_benchmark_ingestion.sql.", file=sql)
        for run_id, timestamp, prompt, fastest, fastest_time in runs:
            measurements = conn.execute("""
                SELECT m.name AS model, mr.success, e.text AS error, mr.response_time AS responseTime,
                       mr.tokens_generated AS tokensGenerated, mr.total_tokens AS totalTokens,
                       mr.time_to_first_token AS timeToFirstToken
                FROM model_results mr
                JOIN models m ON m.id = mr.model_id
                LEFT JOIN errors e ON e.id = mr.error_id
                WHERE mr.run_id = ?
                ORDER BY m.name
            """, (run_id,)).fetchall()
            if not measurements:
                continue
            values = (timestamp, prompt, fastest, fastest_time, json.dumps([dict(row) for row in measurements]))
            print(
                "INSERT INTO benchmark_ingest (run_timestamp, prompt_text, fastest_model, fastest_time, measurements) "
                f"VALUES ({', '.join(escape_val(value) for value in values)});",
                file=sql,
            )
            count += 1
    print(f"Wrote {count} runs after {after} to {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=HISTORY_DB)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--after", metavar="UTC_TIMESTAMP",
                        help="Backfill runs after YYYY-MM-DDTHH:MM:SSZ using the D1 ingestion migration.")
    options = parser.parse_args()
    if options.after:
        try:
            cutoff = datetime.strptime(options.after, "%Y-%m-%dT%H:%M:%S%z")
            if cutoff.strftime("%Y-%m-%dT%H:%M:%SZ") != options.after:
                raise ValueError
        except ValueError:
            parser.error("--after requires YYYY-MM-DDTHH:MM:SSZ")
    if not options.input.is_file():
        print(f"Error: {options.input} not found", file=sys.stderr)
        return 1
    output = options.output or (BACKFILL_SQL if options.after else OUTPUT_SQL)
    if options.input.resolve() == output.resolve():
        parser.error("input and output must be different files")

    conn = sqlite3.connect(options.input.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        if options.after:
            write_backfill(conn, output, options.after)
            return 0

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

        output.write_text("\n".join(out_lines), encoding="utf-8")
        print(f"✓ Wrote {len(out_lines)} SQL statements to {output} ({output.stat().st_size // 1024} KB)")

    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
