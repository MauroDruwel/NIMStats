#!/usr/bin/env python3
"""Sync the NIMStats benchmark model list with the models NVIDIA actually hosts.

Fetches https://integrate.api.nvidia.com/v1/models (no auth required) and
compares it against ALL_MODELS in scripts/test_models.py, then:

  - Removes models NVIDIA no longer publishes
  - Applies curated renames (e.g. dated snapshots replacing unversioned ids)
  - Recommends new chat models ranked by Artificial Analysis intelligence
    index (requires ARTIFICIAL_ANALYSIS_API_KEY; without it only removals
    and renames are applied)

Run manually:
  python scripts/sync_models.py --dry-run          # report only, change nothing
  python scripts/sync_models.py                    # apply changes + print report
  python scripts/sync_models.py --report-path out.md

The scheduled GitHub workflow (.github/workflows/sync-models.yml) runs this
daily and opens/updates a PR with the resulting changes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from manage_models import _read_all_models, _write_all_models  # noqa: E402
from update_intelligence import fetch_intelligence_from_api  # noqa: E402

NVIDIA_MODELS_URL = "https://integrate.api.nvidia.com/v1/models"

# Curated renames: old id -> new id. NVIDIA republishes some models under new
# ids (e.g. dated snapshots); renaming keeps the benchmark history intact.
RENAMES: dict[str, str] = {
    "deepseek-ai/deepseek-v4-flash": "deepseek-ai/deepseek-v4-flash-0731",
}

# Model families on the NVIDIA list that are not text-chat models and are
# therefore not benchmarkable by NIMStats.
NON_CHAT_PATTERNS = (
    "embed", "rerank", "retriev", "bge", "clip", "deplot", "kosmos", "vila",
    "neva", "fuyu", "diffusion", "muse", "riva", "translate", "guard",
    "safety", "reward", "cosmos", "calibrat", "detector", "recurrent",
    "audio", "speech", "asr", "tts",
)


def fetch_nvidia_models() -> set[str]:
    """Fetch the current list of published NVIDIA NIM models."""
    req = urllib.request.Request(
        NVIDIA_MODELS_URL, headers={"User-Agent": "NIMStats model sync"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode())
    return {item["id"] for item in payload.get("data", [])}


def is_chat_model(model_id: str) -> bool:
    lower = model_id.lower()
    return not any(p in lower for p in NON_CHAT_PATTERNS)


def match_aa_candidate(
    model_id: str, api_scores: dict[str, float]
) -> tuple[float | None, str | None]:
    """Mirror update_intelligence.fuzzy_match_score but also return the key."""
    clean_name = (
        model_id.split("/")[-1].lower() if "/" in model_id else model_id.lower()
    )
    tokens = set(re.findall(r"[a-z0-9]+", clean_name))
    if not tokens:
        return None, None

    best_score = 0.0
    best_key = None
    best_val = None
    for key, val in api_scores.items():
        key_tokens = set(re.findall(r"[a-z0-9]+", key.lower()))
        if not key_tokens:
            continue
        overlap = tokens.intersection(key_tokens)
        is_subset = key_tokens.issubset(tokens)
        ratio = len(overlap) / len(tokens)
        if not (is_subset or ratio >= 0.60):
            continue
        # Enforce strict model size checks if present (e.g., 70b, 90b, 49b)
        size_clean = [t for t in tokens if re.match(r"^\d+b$", t)]
        size_key = [t for t in key_tokens if re.match(r"^\d+b$", t)]
        if size_clean and size_key and size_clean[0] != size_key[0]:
            continue
        score = len(overlap) + ratio
        if score > best_score:
            best_score, best_key, best_val = score, key, val
    return (best_val, best_key) if best_key else (None, None)


def plan_changes(
    current: list[str],
    available: set[str],
    aa_scores: dict[str, float],
    min_score: float,
    max_additions: int,
) -> dict:
    to_remove: list[str] = []
    renamed: dict[str, str] = {}

    for model in current:
        target = RENAMES.get(model)
        if target and target in available:
            renamed[model] = target
        elif model not in available:
            to_remove.append(model)

    # Resolve renames so renamed models don't show up as new candidates.
    current_set = {RENAMES.get(m, m) for m in current}

    scored: list[dict] = []
    unscored: list[dict] = []
    for model_id in sorted(available):
        if model_id in current_set or model_id in renamed.values():
            continue
        if not is_chat_model(model_id):
            continue
        if aa_scores:
            score, key = match_aa_candidate(model_id, aa_scores)
            if score is not None and score >= min_score:
                scored.append({"model": model_id, "score": score, "matched": key})
        else:
            # Without benchmark data we only report, never auto-add.
            unscored.append({"model": model_id, "score": None, "matched": None})

    scored.sort(key=lambda c: c["score"], reverse=True)
    return {
        "to_remove": to_remove,
        "renamed": renamed,
        "to_add": scored[:max_additions],
        "potential_adds": scored[max_additions:] + unscored,
        "candidates_total": len(scored) + len(unscored),
        "aa_mode": bool(aa_scores),
    }


def apply_changes(
    current: list[str], to_remove: list[str], renamed: dict[str, str], to_add: list[dict]
) -> list[str]:
    models = [m for m in current if m not in to_remove]
    models = [renamed.get(m, m) for m in models]
    for c in to_add:
        if c["model"] not in models:
            models.append(c["model"])
    _write_all_models(models)
    return models


def build_report(plan: dict, ts: str) -> str:
    removed = plan["to_remove"]
    renamed = plan["renamed"]
    added = plan["to_add"]
    lines = [
        f"# 🤖 NVIDIA model list sync — {ts}",
        "",
        "Automatically generated by the daily [model sync workflow]("
        "https://github.com/MauroDruwel/NIMStats/blob/main/.github/workflows/sync-models.yml).",
        "",
    ]

    total = len(removed) + len(renamed) + len(added)
    if total == 0:
        lines += [
            "## Status",
            "",
            "✅ No changes needed — the model list already matches what NVIDIA publishes.",
        ]
        return "\n".join(lines) + "\n"

    lines.append(f"## Summary — {total} change(s)")
    lines.append("")

    if renamed:
        lines.append(f"### 🔁 Renamed ({len(renamed)})")
        lines.append("")
        lines.append("| Old | New |")
        lines.append("|-----|-----|")
        for old, new in renamed.items():
            lines.append(f"| `{old}` | `{new}` |")
        lines.append("")

    if removed:
        lines.append(f"### ❌ Removed ({len(removed)}) — no longer published by NVIDIA")
        lines.append("")
        for m in removed:
            lines.append(f"- `{m}`")
        lines.append("")

    if added:
        lines.append(f"### ✅ Added ({len(added)}) — new chat models worth benchmarking")
        lines.append("")
        lines.append("| Model | Artificial Analysis match | Intelligence index |")
        lines.append("|-------|---------------------------|--------------------|")
        for c in added:
            match = f"`{c['matched']}`" if c.get("matched") else "—"
            score = f"{c['score']:.1f}" if c.get("score") is not None else "—"
            lines.append(f"| `{c['model']}` | {match} | {score} |")
        lines.append("")

    if not plan["aa_mode"]:
        lines.append(
            "> ℹ️ `ARTIFICIAL_ANALYSIS_API_KEY` was not available, so no new models "
            "were added automatically — only removals and renames were applied. "
            "See the table below for potential candidates once benchmark data is available."
        )
        lines.append("")

    if plan["potential_adds"]:
        lines.append(f"### 📋 Potential candidates ({len(plan['potential_adds'])})")
        lines.append("")
        lines.append("New chat models on NVIDIA not yet in NIMStats (no Artificial Analysis "
                     "score above threshold or no benchmark data available):")
        lines.append("")
        for c in plan["potential_adds"][:15]:
            score = f"{c['score']:.1f}" if c.get("score") is not None else "—"
            lines.append(f"- `{c['model']}` (AA index: {score})")
        if len(plan["potential_adds"]) > 15:
            lines.append(f"- … and {len(plan['potential_adds']) - 15} more")
        lines.append("")

    lines.append("_Changes apply to `ALL_MODELS` in `scripts/test_models.py`; the hourly "
                 "benchmark regenerates `history.db` and the `top/` endpoints after merging._")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="report only, do not modify files")
    parser.add_argument("--report-path", default=None,
                        help="write the markdown report to this file")
    parser.add_argument("--min-score", type=float,
                        default=float(os.getenv("AA_MIN_SCORE", "40")),
                        help="minimum Artificial Analysis index for new additions")
    parser.add_argument("--max-additions", type=int,
                        default=int(os.getenv("MAX_ADDITIONS", "8")),
                        help="maximum number of new models to add per sync")
    args = parser.parse_args()

    current = _read_all_models()
    print(f"NVIDIA model sync: {len(current)} models currently in ALL_MODELS")

    try:
        available = fetch_nvidia_models()
    except Exception as e:
        print(f"Error: failed to fetch NVIDIA model list ({e})", file=sys.stderr)
        return 1
    print(f"Fetched {len(available)} models from {NVIDIA_MODELS_URL}")

    api_key = os.getenv("ARTIFICIAL_ANALYSIS_API_KEY")
    aa_scores = fetch_intelligence_from_api(api_key) if api_key else {}
    if aa_scores:
        print(f"Fetched {len(aa_scores)} intelligence scores from Artificial Analysis")
    elif api_key:
        print("Warning: Artificial Analysis fetch failed — skipping new additions", file=sys.stderr)

    plan = plan_changes(
        current, available, aa_scores, args.min_score, args.max_additions
    )
    report = build_report(plan, datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    if plan["aa_mode"]:
        print(f"Plan: {len(plan['to_remove'])} removed, {len(plan['renamed'])} renamed, "
              f"{len(plan['to_add'])} added")
    else:
        print(f"Plan: {len(plan['to_remove'])} removed, {len(plan['renamed'])} renamed, "
              f"0 added (no Artificial Analysis data)")

    if args.dry_run:
        print(report)
        print(f"Dry run: {len(plan['to_remove']) + len(plan['renamed']) + len(plan['to_add'])} "
              "change(s) would be applied to scripts/test_models.py")
        return 0

    if plan["to_remove"] or plan["renamed"] or plan["to_add"]:
        new_models = apply_changes(current, plan["to_remove"], plan["renamed"], plan["to_add"])
        print(f"Updated scripts/test_models.py: {len(current)} -> {len(new_models)} models")
    else:
        print("No changes needed — scripts/test_models.py left untouched")

    if args.report_path:
        Path(args.report_path).write_text(report, encoding="utf-8")
        print(f"Report written to {args.report_path}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
