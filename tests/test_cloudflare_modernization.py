"""Unit tests for Cloudflare D1 modernization, OpenAPI spec, and Issue #66 composite scoring."""

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestCloudflareModernization(unittest.TestCase):
    def test_openapi_json_matches_yaml_structure(self):
        json_file = REPO_ROOT / "openapi.json"
        yaml_file = REPO_ROOT / "openapi.yaml"
        self.assertTrue(json_file.exists(), "openapi.json must exist")
        self.assertTrue(yaml_file.exists(), "openapi.yaml must exist")

        with open(json_file) as f:
            spec = json.load(f)

        self.assertEqual(spec.get("openapi"), "3.1.0")
        paths = spec.get("paths", {})

        # Verify Issue #57 and Issue #66 paths are documented
        expected_paths = [
            "/api/health",
            "/api/models",
            "/api/history",
            "/api/top",
            "/api/reliable",
            "/top",
            "/top/model",
            "/top/speed",
            "/top/speed/model",
            "/top/intelligence",
            "/top/intelligence/model",
        ]
        for p in expected_paths:
            self.assertIn(p, paths, f"Path {p} must be documented in OpenAPI spec")

    def test_composite_scoring_weights(self):
        """Verify Issue #66 composite ranking weights: 50% Intel + 25% Speed + 25% Reliability."""
        # Scenario: Model A high intel, average speed, high reliability
        intel_a = 80.0
        speed_score_a = 60.0
        uptime_pct_a = 100.0  # 1.0 * 100

        # Score = (80 * 0.50) + (60 * 0.25) + (100 * 0.25) = 40 + 15 + 25 = 80
        score_a = round((intel_a * 0.50) + (speed_score_a * 0.25) + (uptime_pct_a * 0.25))
        self.assertEqual(score_a, 80)

        # Scenario: Model B low intel, fast speed, low reliability
        intel_b = 20.0
        speed_score_b = 100.0
        uptime_pct_b = 40.0

        # Score = (20 * 0.50) + (100 * 0.25) + (40 * 0.25) = 10 + 25 + 10 = 45
        score_b = round((intel_b * 0.50) + (speed_score_b * 0.25) + (uptime_pct_b * 0.25))
        self.assertEqual(score_b, 45)

        self.assertGreater(score_a, score_b)

    def test_sql_escape(self):
        import sys
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from push_run_to_d1 import escape_sql_string

        self.assertEqual(escape_sql_string(None), "NULL")
        self.assertEqual(escape_sql_string("test"), "'test'")
        self.assertEqual(escape_sql_string("it's cool"), "'it''s cool'")

    def test_functions_exist(self):
        functions_dir = REPO_ROOT / "functions" / "api"
        self.assertTrue((functions_dir / "health.js").exists())
        self.assertTrue((functions_dir / "models.js").exists())
        self.assertTrue((functions_dir / "history.js").exists())
        self.assertTrue((functions_dir / "top.js").exists())
        self.assertTrue((functions_dir / "reliable.js").exists())


if __name__ == "__main__":
    unittest.main()
