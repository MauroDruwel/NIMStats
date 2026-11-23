#!/usr/bin/env python3
"""Push benchmark run results to Cloudflare D1 edge database."""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "879f04f8f58e18fb6de847adee291172")
DATABASE_ID = os.environ.get(
    "CLOUDFLARE_D1_DATABASE_ID", "f1f8a2eb-6359-4940-8eaf-7430a9654ff5"
)
INGESTION_MIGRATION = "scripts/d1_benchmark_ingestion.sql"
MEASUREMENT_FIELDS = (
    "responseTime",
    "tokensGenerated",
    "totalTokens",
    "timeToFirstToken",
)


class D1Error(RuntimeError):
    """Actionable D1 failure safe to report in benchmark logs."""


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
    if token or os.environ.get("GITHUB_ACTIONS") == "true":
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


def execute_d1_sql(
    sql: str, token: str, retry_on_401: bool = True, *, params: list[str] | None = None
) -> dict[str, Any]:
    """Execute SQL statement(s) against Cloudflare D1 via the REST API."""
    if not re.fullmatch(r"[0-9a-fA-F]{32}", ACCOUNT_ID):
        raise D1Error(
            "CLOUDFLARE_ACCOUNT_ID must be a 32-character Cloudflare account identifier."
        )
    if not re.fullmatch(
        r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", DATABASE_ID
    ):
        raise D1Error(
            "CLOUDFLARE_D1_DATABASE_ID must be a Cloudflare D1 database UUID."
        )
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/d1/database/{DATABASE_ID}/query"
    query = {"sql": sql, "params": params} if params is not None else {"sql": sql}
    req = urllib.request.Request(
        url,
        data=json.dumps(query).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "NIMStats-Benchmark/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            reply = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if (
            e.code == 401
            and retry_on_401
            and os.environ.get("GITHUB_ACTIONS") != "true"
            and not os.environ.get("CLOUDFLARE_API_TOKEN")
        ):
            new_token = refresh_wrangler_token()
            if new_token and new_token != token:
                return execute_d1_sql(sql, new_token, retry_on_401=False, params=params)
        if e.code in (401, 403):
            raise D1Error(
                f"Cloudflare D1 returned HTTP {e.code}. Check the API token's access to the database."
            ) from None
        raise D1Error(
            f"Cloudflare D1 returned HTTP {e.code}. Check the endpoint and Cloudflare service status."
        ) from None
    except OSError:
        raise D1Error("Could not reach the Cloudflare D1 query endpoint.") from None
    except ValueError:
        raise D1Error("Cloudflare D1 returned an invalid JSON response.") from None

    if (
        not isinstance(reply, dict)
        or reply.get("success") is not True
        or reply.get("errors")
    ):
        raise D1Error(
            "Cloudflare D1 rejected the query. Check the configured token, database, and migration."
        )
    statements = reply.get("result")
    if not isinstance(statements, list) or not statements:
        raise D1Error("Cloudflare D1 omitted the query result.")
    for index, statement in enumerate(statements, start=1):
        if (
            not isinstance(statement, dict)
            or statement.get("success") is not True
            or statement.get("error")
        ):
            raise D1Error(
                f"Cloudflare D1 rejected statement {index}. Check the database migration and permissions."
            )
    return reply


def escape_sql_string(val: str | None) -> str:
    """Safely escape string for SQL literals."""
    if val is None:
        return "NULL"
    escaped = val.replace("'", "''")
    return f"'{escaped}'"


def _require_api_token() -> str:
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        raise D1Error(
            "Set CLOUDFLARE_API_TOKEN in the nimstats-production GitHub Actions environment."
        )
    return token


def check_ingestion() -> None:
    """Confirm configuration, endpoint access, and the ingestion migration without writing a row."""
    response = execute_d1_sql(
        "SELECT 1 FROM sqlite_schema WHERE type = 'trigger' AND name = 'benchmark_ingest_run'",
        _require_api_token(),
    )
    if not response["result"][0].get("results"):
        raise D1Error(
            f"Apply {INGESTION_MIGRATION} to the configured D1 database before running benchmarks."
        )
    print("D1 endpoint reachable and the benchmark ingestion migration is present.")


def _measurements(models: object) -> list[dict[str, Any]]:
    if not isinstance(models, list) or not models:
        raise D1Error("The benchmark run must contain model measurements.")
    measurements = []
    names = set()
    for model in models:
        if not isinstance(model, dict):
            raise D1Error("The benchmark contains a malformed model measurement.")
        name = model.get("model")
        success = model.get("success")
        error = model.get("error")
        if (
            not isinstance(name, str)
            or not name
            or name in names
            or not isinstance(success, bool)
        ):
            raise D1Error(
                "Each model measurement needs a unique name and a boolean success field."
            )
        if error is not None and not isinstance(error, str):
            raise D1Error("A benchmark measurement has a non-text error field.")
        metrics = {field: model.get(field) for field in MEASUREMENT_FIELDS}
        if any(
            value is not None and (type(value) is not int or value < 0)
            for value in metrics.values()
        ):
            raise D1Error(
                "Benchmark time and token measurements must be nonnegative integers or null."
            )
        names.add(name)
        measurements.append(
            {"model": name, "success": success, "error": error or None, **metrics}
        )
    return measurements


def push_run(run: dict[str, Any]) -> bool:
    """Publish and verify one benchmark run in the default branch workflow."""
    if (
        os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("NIMSTATS_BENCHMARK_D1_WRITE") != "1"
    ):
        raise D1Error(
            "D1 benchmark writes are reserved for the default branch benchmark workflow."
        )
    token = _require_api_token()

    timestamp = run.get("timestamp")
    prompt = run.get("prompt")
    if not isinstance(timestamp, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", timestamp
    ):
        raise D1Error("The run requires a UTC timestamp in YYYY-MM-DDTHH:MM:SSZ form.")
    try:
        datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        raise D1Error("The run contains an invalid UTC timestamp.") from None
    if not isinstance(prompt, str) or not prompt.strip():
        raise D1Error("The benchmark run requires its prompt.")

    measurements = _measurements(run.get("models"))
    timed_successes = [
        m for m in measurements if m["success"] and m["responseTime"] is not None
    ]
    fastest = min(timed_successes, key=lambda m: m["responseTime"], default=None)
    fastest_model, fastest_time = (
        (fastest["model"], fastest["responseTime"]) if fastest else ("", 0)
    )

    execute_d1_sql(
        """INSERT INTO benchmark_ingest (run_timestamp, prompt_text, fastest_model, fastest_time, measurements)
           VALUES (?, ?, NULLIF(?, ''), CAST(? AS INTEGER), ?)""",
        token,
        params=[
            timestamp,
            prompt,
            fastest_model,
            str(fastest_time),
            json.dumps(measurements),
        ],
    )
    response = execute_d1_sql(
        """SELECT run_id, models.name AS model, model_results.success, errors.text AS error,
                  response_time AS responseTime, tokens_generated AS tokensGenerated,
                  total_tokens AS totalTokens, time_to_first_token AS timeToFirstToken
           FROM model_results
           JOIN models ON models.id = model_results.model_id
           LEFT JOIN errors ON errors.id = model_results.error_id
           WHERE run_id = (
               SELECT runs.id FROM runs
               JOIN prompts ON prompts.id = runs.prompt_id
               WHERE runs.timestamp = ? AND prompts.text = ?
               ORDER BY runs.id DESC LIMIT 1
           )""",
        token,
        params=[timestamp, prompt],
    )
    persisted = response["result"][0].get("results") or []
    expected = {m["model"]: m for m in measurements}
    actual = {
        row["model"]: {key: value for key, value in row.items() if key != "run_id"}
        for row in persisted
    }
    if actual != expected:
        raise D1Error(
            f"D1 readback for {timestamp} did not match the submitted measurements."
        )
    print(
        f"Verified Cloudflare D1 run {persisted[0]['run_id']} at {timestamp} with {len(persisted)} model results."
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check the configured D1 database without writing.",
    )
    parser.add_argument(
        "input", nargs="?", type=Path, help="Run JSON file, or stdin if omitted."
    )
    args = parser.parse_args()
    try:
        if args.check:
            check_ingestion()
        else:
            run_data = (
                json.loads(args.input.read_text(encoding="utf-8"))
                if args.input
                else json.load(sys.stdin)
            )
            if not isinstance(run_data, dict):
                raise D1Error("The input must be a benchmark JSON object.")
            push_run(run_data)
    except D1Error as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError):
        print(
            "Error: Could not read a benchmark JSON object from the specified input.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
