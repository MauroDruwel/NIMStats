#!/usr/bin/env python3
"""Merge parallel group results and append a single run to history.db."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_utils import write_run  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
BENCHMARK_TYPE = os.getenv("BENCHMARK_TYPE", "main")


def main():
    all_models = []
    timestamp, prompt = None, None

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
    successful = [m for m in all_models if m.get("success")]
    if successful:
        fastest = min(successful, key=lambda x: x.get("responseTime") or float("inf"))
        fastest_model, fastest_time = fastest.get("model", "N/A"), fastest.get("responseTime", 0) or 0
    else:
        fastest_model, fastest_time = "N/A", 0

    merged_run = {
        "timestamp": timestamp, "prompt": prompt, "models": all_models,
        "summary": {"successCount": success_count, "totalModels": total_count,
                    "fastestModel": fastest_model, "fastestTime": fastest_time},
    }

    write_run(merged_run, benchmark_type=BENCHMARK_TYPE)
    print(f"OK Updated history.db ({BENCHMARK_TYPE}): {success_count}/{total_count} passed")

    for group_file in ["results-group1.json", "results-group2.json"]:
        path = SCRIPT_DIR / group_file
        if path.exists():
            path.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
