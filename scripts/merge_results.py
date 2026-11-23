#!/usr/bin/env python3
"""Merge both benchmark groups and publish the complete run to D1."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from push_run_to_d1 import D1Error, push_run

SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> int:
    all_models: list[dict] = []
    groups: list[dict] = []
    group_paths = [SCRIPT_DIR / f"results-group{group}.json" for group in (1, 2)]

    for path in group_paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            print(
                f"Error: Could not load the required artifact {path.name}.",
                file=sys.stderr,
            )
            return 1
        if not isinstance(data, dict) or not isinstance(data.get("models"), list):
            print(f"Error: Invalid benchmark artifact {path.name}.", file=sys.stderr)
            return 1
        groups.append(data)
        all_models.extend(data["models"])

    if not all_models:
        print("Error: Both benchmark groups returned an empty roster.", file=sys.stderr)
        return 1
    if groups[0].get("prompt") != groups[1].get("prompt"):
        print("Error: The benchmark groups used different prompts.", file=sys.stderr)
        return 1
    merged_run = {
        "timestamp": groups[0].get("timestamp"),
        "prompt": groups[0].get("prompt"),
        "models": all_models,
    }

    try:
        push_run(merged_run)
    except D1Error as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    for path in group_paths:
        path.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
