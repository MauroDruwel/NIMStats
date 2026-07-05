#!/usr/bin/env python3
"""Generate best/index.json from history.db — the current #1 model by composite score.

Scoring mirrors the dashboard:
reliability (30%) + intelligence (30%) + speed (20%) + throughput (20%)
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HISTORY_DB = REPO_ROOT / "history.db"
OUTPUT_JSON = REPO_ROOT / "top" / "index.json"
OUTPUT_TXT = REPO_ROOT / "top" / "model.txt"


def load_data(conn):
    runs_q = conn.execute(
        """SELECT r.id, r.timestamp, r.fastest_time, m.name
           FROM runs r
           LEFT JOIN models m ON r.fastest_model_id = m.id
           ORDER BY r.timestamp ASC"""
    ).fetchall()

    # Load model intelligence scores
    models_intel = {}
    for m_name, intel in conn.execute("SELECT name, intelligence_score FROM models").fetchall():
        models_intel[m_name] = intel or 50.0

    if not runs_q:
        return [], models_intel

    runs = []
    for run_id, ts, ft, fm in runs_q:
        results_q = conn.execute(
            """SELECT m.name, mr.success, mr.response_time, mr.tokens_generated
               FROM model_results mr
               JOIN models m ON mr.model_id = m.id
               WHERE mr.run_id = ?""",
            (run_id,),
        ).fetchall()
        runs.append({
            "timestamp": ts,
            "fastestModel": fm or "N/A",
            "fastestTime": ft or 0,
            "models": [
                {"model": m, "success": bool(s), "responseTime": rt, "tokensGenerated": tg}
                for m, s, rt, tg in results_q
            ],
        })
    return runs, models_intel


def compute_stats(runs, models_intel):
    model_names = sorted({m["model"] for r in runs for m in r["models"]})
    stats = {}

    for model in model_names:
        results = [r["models"] and next((m for m in r["models"] if m["model"] == model), None) for r in runs]
        successes = [r for r in results if r and r["success"]]
        tested = [r for r in results if r is not None]
        times = [r["responseTime"] for r in successes if r["responseTime"] and r["responseTime"] > 0]
        tps_arr = [
            r["tokensGenerated"] / (r["responseTime"] / 1000)
            for r in successes
            if r["responseTime"] and r["responseTime"] > 0 and r["tokensGenerated"]
        ]

        stats[model] = {
            "totalRuns": len(tested),
            "successCount": len(successes),
            "uptime": len(successes) / len(tested) if tested else 0,
            "avgTime": sum(times) / len(times) if times else None,
            "bestTime": min(times) if times else None,
            "avgTps": sum(tps_arr) / len(tps_arr) if tps_arr else None,
            "wins": 0,
            "lastSeen": None,
            "intelligence": models_intel.get(model, 50.0)
        }

        for i in range(len(results) - 1, -1, -1):
            if results[i] and results[i]["success"]:
                stats[model]["lastSeen"] = runs[i]["timestamp"]
                break

    for run in runs:
        fm = run["fastestModel"]
        if fm in stats:
            stats[fm]["wins"] += 1

    valid_times = [s["avgTime"] for s in stats.values() if s["avgTime"] is not None]
    valid_tps = [s["avgTps"] for s in stats.values() if s["avgTps"] is not None]
    max_time = max(valid_times) if valid_times else 1
    min_time = min(valid_times) if valid_times else 0
    max_tps = max(valid_tps) if valid_tps else 1
    min_tps = min(valid_tps) if valid_tps else 0

    for s in stats.values():
        speed_score = (
            (1 - (s["avgTime"] - min_time) / max(max_time - min_time, 1)) * 100
            if s["avgTime"] is not None
            else 0
        )
        tps_score = (
            ((s["avgTps"] - min_tps) / max(max_tps - min_tps, 1)) * 100
            if s["avgTps"] is not None
            else 0
        )
        # Revised 4-factor scoring: reliability (30%) + intelligence (30%) + speed (20%) + throughput (20%)
        s["score"] = round(s["uptime"] * 30 + speed_score * 0.2 + tps_score * 0.2 + (s["intelligence"] / 100) * 30)

    return stats


def main():
    if not HISTORY_DB.exists():
        print(f"Error: {HISTORY_DB} not found", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(HISTORY_DB))
    try:
        runs, models_intel = load_data(conn)
        if not runs:
            print("No runs in history.db")
            OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
            empty = {"error": "No benchmark data available", "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
            OUTPUT_JSON.write_text(json.dumps(empty, indent=2), encoding="utf-8")
            OUTPUT_TXT.write_text("", encoding="utf-8")
            return 0
        stats = compute_stats(runs, models_intel)
        best_model = max(stats, key=lambda m: stats[m]["score"])
        s = stats[best_model]
        provider = best_model.split("/")[0]
        output = {
            "best_model": best_model,
            "provider": provider,
            "score": s["score"],
            "intelligence": s["intelligence"],
            "uptime": round(s["uptime"] * 100, 1),
            "avg_response_time_ms": s["avgTime"],
            "best_response_time_ms": s["bestTime"],
            "avg_throughput_tps": round(s["avgTps"], 1) if s["avgTps"] else None,
            "total_runs": s["totalRuns"],
            "success_count": s["successCount"],
            "wins": s["wins"],
            "last_seen": s["lastSeen"],
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_JSON.write_text(json.dumps(output, indent=2), encoding="utf-8")
        OUTPUT_TXT.write_text(best_model, encoding="utf-8")
        print(f"OK Generated top/ -- best model: {best_model} (score: {s['score']})")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
