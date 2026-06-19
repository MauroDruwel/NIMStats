#!/usr/bin/env python3
"""Auxiliary slot benchmark — Ahmed Hassan's agentic_architect aux config."""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_utils import write_run

API_BASE = os.getenv("API_BASE", "https://integrate.api.nvidia.com/v1")
API_KEY = os.getenv("NIM_API_KEY", "")
MODEL_GROUP = os.getenv("MODEL_GROUP", "all")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "300"))
PROMPT = "Write a Python function that checks if a number is prime and returns True or False"

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = SCRIPT_DIR / "results.json"

# Aux slot models from ~/.hermes/config.yaml (actual live config)
# step-3.7-flash dominates (10 slots), kimi-k2.6 for vision, nemotron content safety, nano omni
ALL_MODELS = [
    # Ahmed's actual auxiliary slot models from ~/.hermes/config.yaml
    "stepfun-ai/step-3.7-flash",                    # web_extract, compression, skills_hub, mcp,
                                                     # title_generation, triage_specifier,
                                                     # kanban_decomposer, profile_describer,
                                                     # curator, session_search
    "moonshotai/kimi-k2.6",                         # vision
    "nvidia/nemotron-3.5-content-safety",            # approval
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", # registered nano model
]

GROUP1_MODELS = ALL_MODELS[:4]
GROUP2_MODELS = ALL_MODELS[4:]


def selected_models():
    if MODEL_GROUP == "group1":
        return GROUP1_MODELS
    if MODEL_GROUP == "group2":
        return GROUP2_MODELS
    return ALL_MODELS


def failure_result(model, error):
    return {"model": model, "success": False, "error": error, "responseTime": None,
            "tokensGenerated": None, "totalTokens": None, "response": None}


def normalize_content(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def call_model(model, prompt):
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.7, "top_p": 0.9, "max_tokens": 500, "stream": False}
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{API_BASE}/chat/completions", data=body, method="POST",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    )
    started = time.perf_counter()
    raw_body, status_code = "", 0
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            status_code = response.status
            raw_body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status_code = getattr(exc, "code", 0) or 0
        raw_body = exc.read().decode("utf-8", errors="replace")
    except TimeoutError:
        return failure_result(model, f"Request timed out after {REQUEST_TIMEOUT_SECONDS}s")
    except Exception as exc:
        return failure_result(model, f"Request failed: {exc}")
    response_time = int((time.perf_counter() - started) * 1000)
    if not raw_body.strip():
        return failure_result(model, "Empty response from API")
    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        return {"model": model, "success": False,
                "error": f"Invalid JSON: {exc.msg}", "responseTime": response_time,
                "tokensGenerated": None, "totalTokens": None, "response": raw_body}
    error_obj = data.get("error")
    error_message = ""
    if isinstance(error_obj, dict):
        error_message = str(error_obj.get("message") or "").strip()
    elif isinstance(error_obj, str):
        error_message = error_obj.strip()
    if status_code >= 400:
        error_message = error_message or f"HTTP {status_code}"
        if not error_message.startswith("HTTP"):
            error_message = f"HTTP {status_code}: {error_message}"
        return failure_result(model, error_message)
    if error_message:
        return failure_result(model, error_message)
    choices = data.get("choices")
    content = ""
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict):
                content = normalize_content(message.get("content"))
    if not content.strip():
        return failure_result(model, "No content in response")
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    return {"model": model, "success": True, "responseTime": response_time,
            "tokensGenerated": to_int(usage.get("completion_tokens")),
            "totalokens": to_int(usage.get("total_tokens")),
            "response": content, "error": None}


def compile_output(timestamp, prompt, models):
    successful = [m for m in models if m.get("success")]
    if successful:
        fastest = min(successful, key=lambda x: x.get("responseTime") or float("inf"))
        fastest_model, fastest_time = fastest.get("model", "N/A"), fastest.get("responseTime", 0) or 0
    else:
        fastest_model, fastest_time = "N/A", 0
    return {"timestamp": timestamp, "prompt": prompt, "models": models,
            "summary": {"successCount": len(successful), "totalModels": len(models),
                        "fastestModel": fastest_model, "fastestTime": fastest_time}}


def update_history(new_run):
    write_run(new_run, benchmark_type="aux")
    print(f"History updated (aux): {str(SCRIPT_DIR.parent / 'history.db')}")


def main():
    if not API_KEY:
        print("Error: NIM_API_KEY not set", file=sys.stderr)
        return 1
    models = selected_models()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"Starting AUX slot benchmarks ({MODEL_GROUP or 'all'})...")
    print(f"Timestamp: {timestamp}, Testing {len(models)} models")
    results = []
    for model in models:
        print(f"Testing: {model}")
        result = call_model(model, PROMPT)
        if result.get("success"):
            print(f"  OK ({result['responseTime']}ms, {result.get('tokensGenerated', 0)} tokens)")
        else:
            print(f"  FAIL: {result.get('error') or 'Unknown'}")
        results.append(result)
        time.sleep(0.5)
    final_json = compile_output(timestamp, PROMPT, results)
    OUTPUT_FILE.write_text(json.dumps(final_json, indent=2), encoding="utf-8")
    print(f"Summary: {final_json['summary']['successCount']}/{final_json['summary']['totalModels']}")
    if MODEL_GROUP == "all":
        update_history(final_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
