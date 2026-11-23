#!/usr/bin/env python3
"""Push benchmark run results to Cloudflare D1 edge database."""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "879f04f8f58e18fb6de847adee291172")
DATABASE_ID = os.environ.get("CLOUDFLARE_D1_DATABASE_ID", "f1f8a2eb-6359-4940-8eaf-7430a9654ff5")
MAX_RUNS = 720


def _read_token_from_file() -> tuple[str | None, str | None]:
    wrangler_config = Path.home() / "Library/Preferences/.wrangler/config/default.toml"
    if not wrangler_config.exists():
        wrangler_config = Path.home() / ".wrangler/config/default.toml"
    if not wrangler_config.exists():
        return None, None

    token, exp = None, None
    try:
        with open(wrangler_config) as f:
            for line in f:
                if line.startswith("oauth_token"):
                    token = line.split("=")[1].strip().strip('"\n ')
                elif line.startswith("expiration_time"):
                    exp = line.split("=")[1].strip().strip('"\n ')
    except OSError:
        pass
    return token, exp


def refresh_wrangler_token() -> str | None:
    """Automatically invoke wrangler whoami to refresh local OAuth credentials."""
    import shutil
    import subprocess

    candidates = [
        ["pnpm", "dlx", "wrangler", "whoami"],
        [os.path.expanduser("~/.local/bin/pnpm"), "dlx", "wrangler", "whoami"],
        ["npx", "wrangler", "whoami"],
    ]
    for cmd in candidates:
        if shutil.which(cmd[0]) or os.path.exists(cmd[0]):
            try:
                subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=15,
                    check=False,
                )
                new_token, _ = _read_token_from_file()
                if new_token:
                    return new_token
            except (OSError, subprocess.SubprocessError):
                continue
    return None


def get_auth_token() -> str | None:
    """Retrieve auth token from environment or local Wrangler config with auto-refresh."""
    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if token:
        return token

    token, exp = _read_token_from_file()
    if not token:
        return None

    # Auto-refresh if expired
    if exp:
        try:
            exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) >= exp_dt:
                refreshed = refresh_wrangler_token()
                if refreshed:
                    return refreshed
        except (ValueError, TypeError):
            pass

    return token


def execute_d1_sql(sql: str, token: str, retry_on_401: bool = True) -> dict[str, Any]:
    """Execute SQL statement(s) against Cloudflare D1 via the REST API."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/d1/database/{DATABASE_ID}/query"
    payload = json.dumps({"sql": sql}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "NIMStats-Benchmark/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401 and retry_on_401 and not os.environ.get("CLOUDFLARE_API_TOKEN"):
            new_token = refresh_wrangler_token()
            if new_token and new_token != token:
                return execute_d1_sql(sql, new_token, retry_on_401=False)
        raise


def escape_sql_string(val: str | None) -> str:
    """Safely escape string for SQL literals."""
    if val is None:
        return "NULL"
    escaped = val.replace("'", "''")
    return f"'{escaped}'"


def push_run(run: dict[str, Any], token: str | None = None) -> bool:
    """Push a benchmark run to Cloudflare D1."""
    if not token:
        token = get_auth_token()
    if not token:
        print("Warning: No Cloudflare credentials found (CLOUDFLARE_API_TOKEN). Skipping D1 push.", file=sys.stderr)
        return False

    summary = run.get("summary", {})
    timestamp = run.get("timestamp")
    prompt = run.get("prompt")
    fastest_model = summary.get("fastestModel")
    fastest_time = summary.get("fastestTime") or 0
    models = run.get("models", [])

    statements: list[str] = []

    # 1. Upsert prompt
    if prompt:
        statements.append(f"INSERT OR IGNORE INTO prompts (text) VALUES ({escape_sql_string(prompt)});")

    # 2. Upsert models and errors
    for m in models:
        m_name = m.get("model")
        if m_name:
            statements.append(f"INSERT OR IGNORE INTO models (name) VALUES ({escape_sql_string(m_name)});")
        err = m.get("error")
        if err:
            statements.append(f"INSERT OR IGNORE INTO errors (text) VALUES ({escape_sql_string(err)});")

    # Execute prerequisite dimension inserts
    if statements:
        execute_d1_sql(" ".join(statements), token)

    # 3. Insert run and retrieve ID
    insert_run_sql = (
        f"INSERT INTO runs (timestamp, prompt_id, fastest_model_id, fastest_time) "
        f"SELECT {escape_sql_string(timestamp)}, p.id, m.id, {fastest_time} "
        f"FROM prompts p LEFT JOIN models m ON m.name = {escape_sql_string(fastest_model)} "
        f"WHERE p.text = {escape_sql_string(prompt)} "
        f"RETURNING id;"
    )
    run_resp = execute_d1_sql(insert_run_sql, token)
    run_results = run_resp.get("result", [{}])[0].get("results", [])
    if not run_results:
        print("Error: Failed to insert run into D1", file=sys.stderr)
        return False

    run_id = run_results[0]["id"]

    # 4. Insert model results in batch
    result_statements: list[str] = []
    for m in models:
        m_name = m.get("model")
        if not m_name:
            continue
        success = 1 if m.get("success") else 0
        err = m.get("error")
        rt = m.get("responseTime") if m.get("responseTime") is not None else "NULL"
        tg = m.get("tokensGenerated") if m.get("tokensGenerated") is not None else "NULL"
        tt = m.get("totalTokens") if m.get("totalTokens") is not None else "NULL"
        ttft = m.get("timeToFirstToken") if m.get("timeToFirstToken") is not None else "NULL"

        err_sub = f"(SELECT id FROM errors WHERE text = {escape_sql_string(err)})" if err else "NULL"
        model_sub = f"(SELECT id FROM models WHERE name = {escape_sql_string(m_name)})"

        result_statements.append(
            f"INSERT OR REPLACE INTO model_results "
            f"(run_id, model_id, success, error_id, response_time, tokens_generated, total_tokens, time_to_first_token) "
            f"VALUES ({run_id}, {model_sub}, {success}, {err_sub}, {rt}, {tg}, {tt}, {ttft});"
        )

    # 5. Prune trailing runs beyond MAX_RUNS
    result_statements.append(
        f"DELETE FROM runs WHERE id NOT IN (SELECT id FROM runs ORDER BY timestamp DESC LIMIT {MAX_RUNS});"
    )

    execute_d1_sql(" ".join(result_statements), token)
    print(f"✓ Successfully pushed run #{run_id} ({len(models)} models) to Cloudflare D1 (nimstats-db)")
    return True


def main() -> int:
    if len(sys.argv) > 1:
        file_path = Path(sys.argv[1])
        if not file_path.exists():
            print(f"File not found: {file_path}", file=sys.stderr)
            return 1
        with open(file_path) as f:
            run_data = json.load(f)
    else:
        # Read from stdin
        run_data = json.load(sys.stdin)

    success = push_run(run_data)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
