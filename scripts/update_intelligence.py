#!/usr/bin/env python3
"""Fetch and update model intelligence scores in history.db from Artificial Analysis."""

import os
import sqlite3
import sys
import urllib.request
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
HISTORY_DB = REPO_ROOT / "history.db"

# Robust fallback intelligence mapping for all tested models in NIMStats
FALLBACK_INTELLIGENCE = {
    # Frontier reasoning/flagship models
    "meta/llama-4-maverick-17b-128e-instruct": 95.0,
    "openai/gpt-oss-120b": 94.0,
    "deepseek-ai/deepseek-v4-pro": 93.5,
    "z-ai/glm-5.2": 91.0,
    "mistralai/mistral-large-3-675b-instruct-2512": 88.0,
    
    # High-end open models
    "qwen/qwen3.5-397b-a17b": 83.0,
    "meta/llama-3.3-70b-instruct": 81.0,
    "nvidia/nemotron-3-super-120b-a12b": 80.0,
    "nvidia/llama-3.3-nemotron-super-49b-v1.5": 78.5,
    
    # Mid-range models
    "google/gemma-4-31b-it": 74.0,
    "moonshotai/kimi-k2.6": 72.0,
    "mistralai/mistral-medium-3.5-128b": 70.0,
    "qwen/qwen3.5-122b-a10b": 68.0,
    "qwen/qwen3-next-80b-a3b-instruct": 67.0,
    "meta/llama-3.2-90b-vision-instruct": 66.0,
    "mistralai/mistral-small-4-119b-2603": 65.0,
    
    # Fast / Flash / Smaller models
    "deepseek-ai/deepseek-v4-flash": 60.0,
    "stepfun-ai/step-3.7-flash": 58.0,
    "stepfun-ai/step-3.5-flash": 55.0,
    "minimaxai/minimax-m3": 54.0,
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning": 52.0,
    "minimaxai/minimax-m2.7": 48.0,
}


def init_db_schema(conn: sqlite3.Connection) -> None:
    """Ensure the intelligence_score column exists in the models table."""
    cursor = conn.execute("PRAGMA table_info(models)")
    columns = [row[1] for row in cursor.fetchall()]
    if "intelligence_score" not in columns:
        print("Adding 'intelligence_score' column to 'models' table...")
        conn.execute("ALTER TABLE models ADD COLUMN intelligence_score REAL DEFAULT NULL")
        conn.commit()


def fetch_intelligence_from_api(api_key: str) -> dict[str, float]:
    """Fetch model ratings from Artificial Analysis API."""
    print("Fetching intelligence scores from Artificial Analysis API...")
    url = "https://artificialanalysis.ai/api/v2/language/models"
    headers = {
        "x-api-key": api_key,
        "User-Agent": "NIMStats Benchmark (GitHub Action)"
    }
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            payload = json.loads(response.read().decode())
            data = payload.get("data", [])
            
            api_scores = {}
            for item in data:
                slug = item.get("slug", "").lower()
                name = item.get("name", "").lower()
                
                # Try finding any score related to intelligence/quality in evaluations
                evals = item.get("evaluations", {})
                score = (
                    evals.get("intelligence_index") or
                    evals.get("intelligence") or
                    evals.get("quality_index") or
                    item.get("intelligence_score") or
                    evals.get("score")
                )
                
                if score is not None:
                    try:
                        score_float = float(score)
                        # Store by slug and name
                        if slug:
                            api_scores[slug] = score_float
                        if name:
                            api_scores[name] = score_float
                    except ValueError:
                        continue
            
            return api_scores
    except Exception as e:
        print(f"Warning: Failed to fetch from Artificial Analysis API ({e}). Using fallbacks.", file=sys.stderr)
        return {}


def fuzzy_match_score(model_name: str, api_scores: dict[str, float]) -> float | None:
    """Fuzzy match NIMStats model name to Artificial Analysis keys."""
    # Clean model name: meta/llama-3.3-70b-instruct -> llama-3.3-70b-instruct
    clean_name = model_name.split("/")[-1].lower() if "/" in model_name else model_name.lower()
    
    # Exact match on cleaned name
    if clean_name in api_scores:
        return api_scores[clean_name]
        
    # Match replacing characters
    normalized = clean_name.replace(".", "-").replace("_", "-")
    if normalized in api_scores:
        return api_scores[normalized]
        
    # Check if NIMStats name contains the API key, or vice-versa
    for key, val in api_scores.items():
        if key in clean_name or clean_name in key:
            return val
            
    return None


def main() -> int:
    if not HISTORY_DB.exists():
        print(f"Error: Database {HISTORY_DB} not found", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(HISTORY_DB))
    try:
        init_db_schema(conn)
        
        # Check API Key
        api_key = os.environ.get("ARTIFICIAL_ANALYSIS_API_KEY")
        api_scores = fetch_intelligence_from_api(api_key) if api_key else {}
        
        # Query models
        models = [row[0] for row in conn.execute("SELECT name FROM models").fetchall()]
        
        updated_count = 0
        for model in models:
            score = None
            
            # 1. Try matching with API results
            if api_scores:
                score = fuzzy_match_score(model, api_scores)
                
            # 2. Fall back to local dataset
            if score is None:
                score = FALLBACK_INTELLIGENCE.get(model)
                
            # 3. Last fallback: default to 50 if nothing matches
            if score is None:
                score = 50.0
                
            # Update database record
            conn.execute(
                "UPDATE models SET intelligence_score = ? WHERE name = ?",
                (score, model)
            )
            updated_count += 1
            
        conn.commit()
        print(f"OK: Successfully updated intelligence scores for {updated_count} models in history.db")
        
    finally:
        conn.close()
        
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
