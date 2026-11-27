#!/usr/bin/env python3

import argparse
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_BASE = os.getenv("API_BASE", "https://integrate.api.nvidia.com/v1")
API_KEY = os.getenv("NIM_API_KEY", "")
MODEL_GROUP = os.getenv("MODEL_GROUP", "all")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "300"))
PROMPT = "Write a Python function that checks if a number is prime and returns True or False"
PROFILE_PROMPTS = {
    "code": PROMPT,
    "json": 'Return exactly one JSON object with the integer field "answer" set to the product of 6 and 7.',
    "tool": "Use the report_value tool to report the product of 6 and 7. Do not answer in prose.",
}
REPORT_VALUE_TOOL = {
    "type": "function",
    "function": {
        "name": "report_value",
        "description": "Report an integer result.",
        "parameters": {
            "type": "object",
            "properties": {"value": {"type": "integer"}},
            "required": ["value"],
            "additionalProperties": False,
        },
    },
}

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = SCRIPT_DIR / "results.json"

ALL_MODELS = [
    "nvidia/nemotron-3.5-bolt-e4b",
    "nvidia/nemotron-3.5-super-vl-120b-a12b",
    "poolside/laguna-xs-2.1",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    "nvidia/nemotron-3-ultra-550b-a55b",
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "z-ai/glm-5.3-flash",
    "stepfun-ai/step-5-preview",
    "mistralai/mistral-large-4-1t-a52b",
    "minimaxai/minimax-m3.1-flash",
    "moonshotai/kimi-k3.1-pro",
]

GLM_THINKING_MODELS = {"z-ai/glm-5.3-flash"}

GROUP1_MODELS = ALL_MODELS[: len(ALL_MODELS) // 2 + len(ALL_MODELS) % 2]

GROUP2_MODELS = ALL_MODELS[len(ALL_MODELS) // 2 + len(ALL_MODELS) % 2 :]


def selected_models() -> list[str]:
    if MODEL_GROUP == "group1":
        return GROUP1_MODELS
    if MODEL_GROUP == "group2":
        return GROUP2_MODELS
    return ALL_MODELS


def failure_result(model: str, error: str) -> dict[str, Any]:
    return {
        "model": model,
        "success": False,
        "error": error,
        "responseTime": None,
        "tokensGenerated": None,
        "totalTokens": None,
        "timeToFirstToken": None,
        "response": None,
    }


def is_expected_value(text: str, field: str) -> bool:
    """Check the exact expected object, including its field type."""
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return False
    return (
        isinstance(value, dict) and value.keys() == {field}
        and type(value[field]) is int and value[field] == 42
    )


def call_model(model: str, prompt: str, profile: str = "code") -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 500,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if model in GLM_THINKING_MODELS:
        # GLM-5.3 thinking is always enabled; cap effort so this short benchmark
        # can reach a final answer instead of spending the whole output budget reasoning.
        payload.update({"max_tokens": 2048, "reasoning_effort": "low"})
    if profile == "tool":
        payload.update({"tools": [REPORT_VALUE_TOOL], "tool_choice": "auto"})
    body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        f"{API_BASE}/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )

    started = time.perf_counter()
    reasoning_chars = 0
    finish_reason: str | None = None
    completed = False
    tool_calls: dict[int, dict[str, str]] = {}

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            content_parts: list[str] = []
            time_to_first_token_ms: int | None = None
            completion_tokens: int | None = None
            total_tokens: int | None = None

            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[len("data:"):].strip()
                if data_str == "[DONE]":
                    completed = True
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                if not isinstance(chunk, dict):
                    continue
                if chunk.get("error"):
                    return failure_result(model, "Provider returned an error in the stream")

                # Extract content from delta
                choices = chunk.get("choices")
                if isinstance(choices, list) and choices and isinstance(choices[0], dict):
                    choice = choices[0]
                    delta = choice.get("delta") or {}
                    if not isinstance(delta, dict):
                        continue
                    text = delta.get("content") or ""
                    reasoning = delta.get("reasoning_content") or delta.get("reasoning") or ""
                    if isinstance(reasoning, str):
                        reasoning_chars += len(reasoning)
                    finish_reason = choice.get("finish_reason") or finish_reason
                    if isinstance(text, str) and text:
                        if time_to_first_token_ms is None and text.strip():
                            time_to_first_token_ms = int((time.perf_counter() - started) * 1000)
                        content_parts.append(text)
                    parts = delta.get("tool_calls")
                    if profile == "tool" and isinstance(parts, list):
                        for part in parts:
                            if not isinstance(part, dict) or not isinstance(part.get("function"), dict):
                                continue
                            index = part.get("index", 0)
                            if not isinstance(index, int):
                                continue
                            call = tool_calls.setdefault(index, {"name": "", "arguments": ""})
                            for key, value in part["function"].items():
                                if key in call and isinstance(value, str):
                                    call[key] += value

                usage = chunk.get("usage")
                if isinstance(usage, dict):
                    if isinstance(usage.get("completion_tokens"), int):
                        completion_tokens = usage["completion_tokens"]
                    if isinstance(usage.get("total_tokens"), int):
                        total_tokens = usage["total_tokens"]

            response_time = int((time.perf_counter() - started) * 1000)
            content = "".join(content_parts)

    except urllib.error.HTTPError as exc:
        exc.close()
        return failure_result(model, f"HTTP {exc.code}")
    except TimeoutError:
        return failure_result(model, f"Request timed out after {REQUEST_TIMEOUT_SECONDS}s")
    except (OSError, http.client.HTTPException) as exc:
        return failure_result(model, f"Request failed ({type(exc).__name__})")

    if not completed and not finish_reason:
        return failure_result(model, "Stream closed before completion")
    if profile == "tool":
        call = next(iter(tool_calls.values()), None) if len(tool_calls) == 1 else None
        if not call or call["name"] != "report_value" or not is_expected_value(call["arguments"], "value"):
            return failure_result(model, "Expected one report_value tool call with integer value 42")
        content = call["arguments"]
    elif profile == "json" and not is_expected_value(content, "answer"):
        return failure_result(model, "Expected a JSON object with integer answer 42")
    elif not content.strip():
        details = []
        if reasoning_chars:
            details.append("reasoning only")
        if finish_reason:
            details.append(f"finish_reason={finish_reason}")
        if details:
            return failure_result(model, f"No final content in response ({', '.join(details)})")
        return failure_result(model, "No content in response")

    return {
        "model": model,
        "success": True,
        "responseTime": response_time,
        "tokensGenerated": completion_tokens,
        "totalTokens": total_tokens,
        "timeToFirstToken": time_to_first_token_ms,
        "response": content,
        "error": None,
    }


def compile_output(timestamp: str, prompt: str, models: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [item for item in models if item.get("success")]
    success_count = len(successful)
    total_count = len(models)

    if successful:
        fastest = min(
            successful,
            key=lambda item: item.get("responseTime")
            if isinstance(item.get("responseTime"), int)
            else float("inf"),
        )
        fastest_model = fastest.get("model", "N/A")
        fastest_time = fastest.get("responseTime", 0) or 0
    else:
        fastest_model = "N/A"
        fastest_time = 0

    return {
        "timestamp": timestamp,
        "prompt": prompt,
        "models": models,
        "summary": {
            "successCount": success_count,
            "totalModels": total_count,
            "fastestModel": fastest_model,
            "fastestTime": fastest_time,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect NVIDIA NIM benchmark results.")
    parser.add_argument("--profile", choices=PROFILE_PROMPTS, default="code")
    parser.add_argument("--output", type=Path, help="Path to the results JSON file.")
    options = parser.parse_args()

    if not API_KEY:
        print("Error: NIM_API_KEY environment variable not set", file=sys.stderr)
        return 1

    models = selected_models()
    prompt = PROFILE_PROMPTS[options.profile]
    output = options.output or (
        OUTPUT_FILE if options.profile == "code" else SCRIPT_DIR / f"results-{options.profile}.json"
    )
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    group_label = f" (Group: {MODEL_GROUP})" if MODEL_GROUP else ""
    print(f"Starting NVIDIA NIM Model Benchmarks{group_label}...")
    print(f"Timestamp: {timestamp}")
    print(f"Testing {len(models)} models...")
    print()

    results: list[dict[str, Any]] = []
    for model in models:
        print(f"Testing: {model}")
        result = call_model(model, prompt, options.profile)
        if result.get("success"):
            ttft_str = f", TTFT {result['timeToFirstToken']}ms" if result.get("timeToFirstToken") is not None else ""
            print(f"  ✓ Success ({result['responseTime']}ms{ttft_str}, {result.get('tokensGenerated', 0)} tokens)")
        else:
            print(f"  ✗ Failed: {result.get('error') or 'Unknown error'}")
        results.append(result)
        time.sleep(0.5)

    print()
    print("Compiling results...")

    final_json = compile_output(timestamp, prompt, results)
    final_json["profile"] = options.profile
    output.write_text(json.dumps(final_json, indent=2), encoding="utf-8")

    success_count = final_json["summary"]["successCount"]
    total_count = final_json["summary"]["totalModels"]
    print(f"Results saved to {output}")
    print(f"Summary: {success_count}/{total_count} successful")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
