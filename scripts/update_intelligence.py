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
    url = "https://artificialanalysis.ai/api/v2/data/llms/models"
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
                
                evals = item.get("evaluations", {})
                score = (
                    evals.get("artificial_analysis_intelligence_index") or
                    evals.get("intelligence_index") or
                    evals.get("intelligence") or
                    evals.get("quality_index") or
                    item.get("intelligence_score") or
                    evals.get("score")
                )
                
                if score is not None:
                    try:
                        score_float = float(score)
                        if slug:
                            api_scores[slug] = score_float
                        if name:
                            api_scores[name] = score_float
                    except ValueError:
                        continue
            
            return api_scores
    except Exception as e:
        print(f"Warning: Failed to fetch from Artificial Analysis API ({e}). Leaving scores as NULL/N/A.", file=sys.stderr)
        return {}


def fuzzy_match_score(model_name: str, api_scores: dict[str, float]) -> float | None:
    """Fuzzy match NIMStats model name to Artificial Analysis keys using token overlap."""
    clean_name = model_name.split("/")[-1].lower() if "/" in model_name else model_name.lower()
    
    import re
    # Tokenize the clean name
    tokens = set(re.findall(r'[a-z0-9]+', clean_name))
    if not tokens:
        return None
        
    best_match = None
    best_score = 0.0
    
    for key, val in api_scores.items():
        key_tokens = set(re.findall(r'[a-z0-9]+', key.lower()))
        if not key_tokens:
            continue
        overlap = tokens.intersection(key_tokens)
        
        is_subset = key_tokens.issubset(tokens)
        ratio = len(overlap) / len(tokens)
        
        if is_subset or ratio >= 0.60:
            # Enforce strict model size checks if present (e.g., 70b, 90b, 49b)
            size_tokens_clean = [t for t in tokens if re.match(r'^\d+b$', t)]
            size_tokens_key = [t for t in key_tokens if re.match(r'^\d+b$', t)]
            if size_tokens_clean and size_tokens_key:
                if size_tokens_clean[0] != size_tokens_key[0]:
                    continue  # Size mismatch, skip
                    
            # Score by overlap size, and break ties with ratio
            score = len(overlap) + ratio
            if score > best_score:
                best_score = score
                best_match = val
                
    return best_match


def main() -> int:
    if not HISTORY_DB.exists():
        print(f"Error: Database {HISTORY_DB} not found", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(HISTORY_DB))
    try:
        init_db_schema(conn)
        
        # Check API Key
        api_key = os.environ.get("ARTIFICIAL_ANALYSIS_API_KEY")
        if not api_key:
            print("Warning: ARTIFICIAL_ANALYSIS_API_KEY env var is missing. Skipping API fetch (resetting scores to NULL/N/A).")
            
        api_scores = fetch_intelligence_from_api(api_key) if api_key else {}
        
        # Query models
        models = [row[0] for row in conn.execute("SELECT name FROM models").fetchall()]
        
        updated_count = 0
        for model in models:
            score = None
            
            # Try matching with API results if we have them
            if api_scores:
                score = fuzzy_match_score(model, api_scores)
                
            # Update database record (None -> NULL in SQLite)
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
