#!/usr/bin/env python3
"""Merge parallel group results and append a single run to history.db."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from push_run_to_d1 import push_run

SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> int:
    all_models: list[dict] = []
    timestamp: str | None = None
    prompt: str | None = None

    for group_file in ["results-group1.json", "results-group2.json"]:
        path = SCRIPT_DIR / group_file
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            all_models.extend(data.get("models", []))
            if not timestamp:
                timestamp = data.get("timestamp")
                prompt = data.get("prompt")

    if not all_models:
        print("No results found!", file=sys.stderr)
        return 1

    success_count = sum(1 for m in all_models if m.get("success"))
    total_count = len(all_models)
    fastest_model = "N/A"
    fastest_time = 0

    successful = [m for m in all_models if m.get("success")]
    if successful:
        fastest = min(successful, key=lambda x: x.get("responseTime") or float("inf"))
        fastest_model = fastest.get("model", "N/A")
        fastest_time = fastest.get("responseTime", 0) or 0

    merged_run = {
        "timestamp": timestamp,
        "prompt": prompt,
        "models": all_models,
        "summary": {
            "successCount": success_count,
            "totalModels": total_count,
            "fastestModel": fastest_model,
            "fastestTime": fastest_time,
        },
    }

    # Push directly to Cloudflare D1 edge database
    success = push_run(merged_run)
    if not success:
        print("Error: Failed to push benchmark run to Cloudflare D1", file=sys.stderr)
        return 1

    for group_file in ["results-group1.json", "results-group2.json"]:
        path = SCRIPT_DIR / group_file
        if path.exists():
            path.unlink()
    print("✓ Cleaned up temporary group files")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
