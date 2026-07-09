#!/usr/bin/env python3
"""Generate specialized top model endpoints from history.db.

Outputs:
- Balanced (top/index.json, top/model.txt): reliability (30%) + intelligence (30%) + speed (20%) + throughput (20%)
- Speed (top/speed.json, top/speed.txt): speed (50%) + throughput (50%)
- Intelligence (top/intelligence.json, top/intelligence.txt): intelligence (70%) + reliability (30%)
"""

import json
import sqlite3
import sys
from datetime import timezone, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HISTORY_DB = REPO_ROOT / "history.db"
TOP_DIR = REPO_ROOT / "top"


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
        models_intel[m_name] = intel

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
            "intelligence": models_intel.get(model)
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
        
        intel_val = s["intelligence"] if s["intelligence"] is not None else 50.0

        # Compute specialized scores
        s["score_balanced"] = round(s["uptime"] * 30 + speed_score * 0.2 + tps_score * 0.2 + (intel_val / 100) * 30)
        s["score_speed"] = round(speed_score * 0.5 + tps_score * 0.5)
        s["score_intel"] = round((intel_val / 100) * 70 + s["uptime"] * 30)

    return stats


def write_endpoint(slug: str, best_model: str, stats_record: dict, key_name: str) -> None:
    """Helper to write the JSON and raw text files for a specific category."""
    output_json = TOP_DIR / f"{slug}.json" if slug != "index" else TOP_DIR / "index.json"
    output_txt = TOP_DIR / f"{slug}.txt" if slug != "index" else TOP_DIR / "model.txt"

    output = {
        "best_model": best_model,
        "provider": best_model.split("/")[0] if "/" in best_model else best_model,
        "score": stats_record[key_name],
        "intelligence": stats_record["intelligence"],
        "uptime": round(stats_record["uptime"] * 100, 1),
        "avg_response_time_ms": stats_record["avgTime"],
        "best_response_time_ms": stats_record["bestTime"],
        "avg_throughput_tps": round(stats_record["avgTps"], 1) if stats_record["avgTps"] else None,
        "total_runs": stats_record["totalRuns"],
        "success_count": stats_record["successCount"],
        "wins": stats_record["wins"],
        "last_seen": stats_record["lastSeen"],
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    
    output_json.write_text(json.dumps(output, indent=2), encoding="utf-8")
    output_txt.write_text(best_model, encoding="utf-8")
    print(f"OK Generated top/{slug} -- best model: {best_model} (score: {stats_record[key_name]})")


def main():
    if not HISTORY_DB.exists():
        print(f"Error: {HISTORY_DB} not found", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(HISTORY_DB))
    try:
        runs, models_intel = load_data(conn)
        TOP_DIR.mkdir(parents=True, exist_ok=True)
        
        if not runs:
            print("No runs in history.db")
            empty = {"error": "No benchmark data available", "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
            (TOP_DIR / "index.json").write_text(json.dumps(empty, indent=2), encoding="utf-8")
            (TOP_DIR / "model.txt").write_text("", encoding="utf-8")
            return 0
            
        stats = compute_stats(runs, models_intel)
        
        # Filter out models that failed the last test (likely offline)
        last_run_successes = set()
        if runs:
            last_run = runs[-1]
            for m_res in last_run.get("models", []):
                if m_res.get("success"):
                    last_run_successes.add(m_res.get("model"))
                    
        eligible_models = [m for m in stats if m in last_run_successes]
        if not eligible_models:
            print("Warning: No models succeeded in the last run. Falling back to all models.")
            eligible_models = list(stats.keys())
        
        # 1. Balanced
        best_balanced = max(eligible_models, key=lambda m: stats[m]["score_balanced"])
        write_endpoint("index", best_balanced, stats[best_balanced], "score_balanced")
        
        # 2. Speed
        best_speed = max(eligible_models, key=lambda m: stats[m]["score_speed"])
        write_endpoint("speed", best_speed, stats[best_speed], "score_speed")
        
        # 3. Intelligence
        best_intel = max(eligible_models, key=lambda m: stats[m]["score_intel"])
        write_endpoint("intelligence", best_intel, stats[best_intel], "score_intel")
        
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
