"""Exercise the benchmark writer against a local SQLite D1 fixture."""

import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import merge_results
import push_run_to_d1 as ingestion


class TestIngestion(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript((SCRIPTS / "d1_schema.sql").read_text(encoding="utf-8"))
        migration = (ROOT / ingestion.INGESTION_MIGRATION).read_text(encoding="utf-8")
        self.db.executescript(migration)
        self.db.executescript(migration)
        self.token = "fixture-token"
        self.enterContext(
            patch.dict(
                os.environ,
                {
                    "CLOUDFLARE_API_TOKEN": self.token,
                    "GITHUB_ACTIONS": "true",
                    "NIMSTATS_BENCHMARK_D1_WRITE": "1",
                },
            )
        )
        self.http = self.enterContext(
            patch.object(
                ingestion.urllib.request, "urlopen", side_effect=self.d1_request
            )
        )
        self.log = self.enterContext(redirect_stdout(io.StringIO()))
        self.run_data = {
            "timestamp": "2026-11-23T20:00:00Z",
            "prompt": "Check this prompt's apostrophe and UTF-8 ✓",
            "models": [
                {
                    "model": "fast",
                    "success": True,
                    "responseTime": 50,
                    "tokensGenerated": 8,
                    "totalTokens": 15,
                    "timeToFirstToken": 15,
                },
                {"model": "down", "success": False, "error": "Provider isn't ready"},
            ],
        }

    def d1_request(self, request, **_):
        query = json.loads(request.data)
        self.assertEqual(request.get_header("Authorization"), f"Bearer {self.token}")
        with self.db:
            rows = self.db.execute(query["sql"], query.get("params", [])).fetchall()
        return io.BytesIO(
            json.dumps(
                {
                    "success": True,
                    "result": [
                        {"success": True, "results": [dict(row) for row in rows]}
                    ],
                }
            ).encode()
        )

    def test_migration_and_replay(self):
        ingestion.check_ingestion()
        self.assertTrue(ingestion.push_run(self.run_data))
        initial_run = tuple(self.db.execute("SELECT * FROM runs").fetchone())
        self.assertTrue(ingestion.push_run(self.run_data))
        self.assertEqual(
            [tuple(row) for row in self.db.execute("SELECT * FROM runs")], [initial_run]
        )
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM model_results").fetchone()[0], 2
        )
        self.assertIn(
            "Verified Cloudflare D1 run 1 at 2026-11-23T20:00:00Z with 2 model results",
            self.log.getvalue(),
        )
        submitted = json.loads(self.http.call_args_list[1].args[0].data)
        self.assertNotIn("apostrophe", submitted["sql"])
        self.assertEqual(submitted["params"][1], self.run_data["prompt"])

    def test_single_insert_rolls_back_a_partial_failure(self):
        # The second measurement violates model_results.success NOT NULL after
        # the trigger has inserted dimensions and the run header.
        measurements = [*self.run_data["models"], {"model": "bad", "success": None}]
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO benchmark_ingest VALUES (?, ?, ?, ?, ?)",
                (
                    self.run_data["timestamp"],
                    self.run_data["prompt"],
                    "fast",
                    50,
                    json.dumps(measurements),
                ),
            )
        for table in ("prompts", "models", "errors", "runs", "model_results"):
            self.assertEqual(
                self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0
            )

    def test_retention_keeps_720_runs_and_breaks_time_ties_by_id(self):
        self.db.execute("INSERT INTO prompts (text) VALUES ('older prompt')")
        self.db.execute("INSERT INTO models (name) VALUES ('retired model')")
        old = datetime(2026, 10, 20, tzinfo=timezone.utc)
        timestamps = [
            (old + timedelta(hours=max(index - 1, 0))).strftime("%Y-%m-%dT%H:%M:%SZ")
            for index in range(720)
        ]
        self.db.executemany(
            "INSERT INTO runs (timestamp, prompt_id) VALUES (?, 1)",
            [(stamp,) for stamp in timestamps],
        )
        self.db.executemany(
            "INSERT INTO model_results (run_id, model_id) VALUES (?, 1)", [(1,), (2,)]
        )
        self.assertTrue(ingestion.push_run(self.run_data))
        self.assertEqual(
            tuple(self.db.execute("SELECT COUNT(*), MIN(id) FROM runs").fetchone()),
            (720, 2),
        )
        self.assertIsNone(
            self.db.execute("SELECT 1 FROM model_results WHERE run_id = 1").fetchone()
        )
        self.assertIsNotNone(
            self.db.execute("SELECT 1 FROM model_results WHERE run_id = 2").fetchone()
        )

    def test_missing_migration_or_token_fail_preflight(self):
        self.db.execute("DROP TRIGGER benchmark_ingest_run")
        with self.assertRaisesRegex(ingestion.D1Error, ingestion.INGESTION_MIGRATION):
            ingestion.check_ingestion()
        self.http.reset_mock()
        with (
            patch.dict(os.environ, {"CLOUDFLARE_API_TOKEN": ""}),
            self.assertRaisesRegex(ingestion.D1Error, "CLOUDFLARE_API_TOKEN"),
        ):
            ingestion.check_ingestion()
        self.http.assert_not_called()

    def test_local_invocation_cannot_write(self):
        with (
            patch.dict(os.environ, {"GITHUB_ACTIONS": ""}),
            self.assertRaisesRegex(ingestion.D1Error, "default branch"),
        ):
            ingestion.push_run(self.run_data)
        self.http.assert_not_called()

    def test_http_success_with_sql_failure_is_rejected_without_raw_details(self):
        for response in (
            {"success": False, "errors": [{"message": self.token}]},
            {"success": True, "result": [{"success": False, "error": self.token}]},
        ):
            with (
                patch.object(
                    ingestion.urllib.request,
                    "urlopen",
                    return_value=io.BytesIO(json.dumps(response).encode()),
                ),
                self.assertRaises(ingestion.D1Error) as raised,
            ):
                ingestion.execute_d1_sql("SELECT 1", self.token)
            self.assertNotIn(self.token, str(raised.exception))

    def test_merge_requires_both_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "results-group1.json").write_text(
                json.dumps(self.run_data), encoding="utf-8"
            )
            with (
                patch.object(merge_results, "SCRIPT_DIR", folder),
                redirect_stderr(io.StringIO()) as error,
            ):
                self.assertEqual(merge_results.main(), 1)
            self.assertIn("results-group2.json", error.getvalue())
        self.http.assert_not_called()


if __name__ == "__main__":
    unittest.main()
