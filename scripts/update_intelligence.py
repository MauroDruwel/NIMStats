#!/usr/bin/env python3
"""Fetch and update model intelligence scores in Cloudflare D1 from Artificial Analysis."""

import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from push_run_to_d1 import escape_sql_string, execute_d1_sql, get_auth_token


def fetch_intelligence_from_api(api_key: str) -> dict[str, float]:
    """Fetch model ratings from Artificial Analysis API."""
    print("Fetching intelligence scores from Artificial Analysis API...")
    base_url = "https://artificialanalysis.ai/api/v2/language/models/free"
    headers = {
        "x-api-key": api_key,
        "User-Agent": "NIMStats Benchmark (GitHub Action)"
    }
    
    api_scores: dict[str, float] = {}
    page = 1
    
    while True:
        url = f"{base_url}?page={page}&page_size=200"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                payload = json.loads(response.read().decode())
                data = payload.get("data", [])
                
                for item in data:
                    slug = item.get("slug", "").lower()
                    name = item.get("name", "").lower()
                    model_id = item.get("id", "").lower()
                    
                    evals = item.get("evaluations", {}) or {}
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
                            if model_id:
                                api_scores[model_id] = score_float
                        except ValueError:
                            continue
                
                pagination = payload.get("pagination", {})
                if pagination.get("has_more") and page < pagination.get("total_pages", 1):
                    page += 1
                else:
                    break
        except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
            print(f"Warning: Failed to fetch from Artificial Analysis API ({e}). Leaving scores as NULL/N/A.", file=sys.stderr)
            break
            
    return api_scores


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
            if size_tokens_clean and size_tokens_key and size_tokens_clean[0] != size_tokens_key[0]:
                continue  # Size mismatch, skip
                    
            # Score by overlap size, and break ties with ratio
            score = len(overlap) + ratio
            if score > best_score:
                best_score = score
                best_match = val
                
    return best_match


def main() -> int:
    token = get_auth_token()
    if not token:
        print("Error: No Cloudflare API token found for D1 update", file=sys.stderr)
        return 1

    # Check API Key
    api_key = os.environ.get("ARTIFICIAL_ANALYSIS_API_KEY")
    if not api_key:
        print("Warning: ARTIFICIAL_ANALYSIS_API_KEY env var is missing. Skipping API fetch (resetting scores to NULL/N/A).")

    api_scores = fetch_intelligence_from_api(api_key) if api_key else {}

    # Query models directly from Cloudflare D1
    try:
        models_resp = execute_d1_sql("SELECT name FROM models ORDER BY name ASC;", token)
        model_rows = models_resp.get("result", [{}])[0].get("results", [])
        models = [r["name"] for r in model_rows]
    except (OSError, RuntimeError, KeyError, IndexError) as e:
        print(f"Warning: Failed to fetch models from D1 ({e}), falling back to test_models.ALL_MODELS")
        from test_models import ALL_MODELS
        models = ALL_MODELS

    d1_stmts = []
    for model in models:
        s = fuzzy_match_score(model, api_scores) if api_scores else None
        score_val = str(s) if s is not None else "NULL"
        d1_stmts.append(f"UPDATE models SET intelligence_score = {score_val} WHERE name = {escape_sql_string(model)};")

    if d1_stmts:
        execute_d1_sql(" ".join(d1_stmts), token)
        print(f"OK: Successfully updated intelligence scores for {len(models)} models on Cloudflare D1")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
