#!/bin/bash

# NVIDIA NIM Model Benchmark Script
# Tests latest code generation models from build.nvidia.com
# Supports parallel execution via MODEL_GROUP environment variable

set -e

API_KEY="${NIM_API_KEY}"
API_BASE="https://integrate.api.nvidia.com/v1"
MODEL_GROUP="${MODEL_GROUP:-all}"
OUTPUT_FILE="results.json"
HISTORY_FILE="../history.json"

PROMPT="Write a Python function that checks if a number is prime and returns True or False"

# All models grouped for parallel execution
ALL_MODELS=(
    "deepseek-ai/deepseek-v4-flash"
    "deepseek-ai/deepseek-v4-pro"
    "deepseek-ai/deepseek-v3.2"
    "z-ai/glm-5.1"
    "z-ai/glm-4.7"
    "minimax/minimax-m2.7"
    "minimax/minimax-m2.5"
    "nvidia/nemotron-3-super-120b-a12b"
    "nvidia/nemotron-4-340b-instruct"
    "nvidia/llama-3.1-nemotron-ultra-253b-v1"
    "moonshotai/kimi-k2.5"
    "moonshotai/kimi-k2-instruct"
    "gpt-oss/gpt-oss-120b"
    "google/gemma-4-31b-it"
    "qwen/qwen3-coder-480b-a35b-instruct"
    "qwen/qwen2.5-coder-32b-instruct"
    "qwen/qwen3.5-397b-a17b"
    "mistralai/devstral-2-123b-instruct-2512"
    "mistralai/mistral-large-3-675b-instruct-2512"
    "meta/llama-3.1-405b-instruct"
)

# Split models into groups for parallel execution
GROUP1_MODELS=(
    "deepseek-ai/deepseek-v4-flash"
    "deepseek-ai/deepseek-v4-pro"
    "deepseek-ai/deepseek-v3.2"
    "z-ai/glm-5.1"
    "z-ai/glm-4.7"
    "minimax/minimax-m2.7"
    "minimax/minimax-m2.5"
    "nvidia/nemotron-3-super-120b-a12b"
    "nvidia/nemotron-4-340b-instruct"
    "nvidia/llama-3.1-nemotron-ultra-253b-v1"
)

GROUP2_MODELS=(
    "moonshotai/kimi-k2.5"
    "moonshotai/kimi-k2-instruct"
    "gpt-oss/gpt-oss-120b"
    "google/gemma-4-31b-it"
    "qwen/qwen3-coder-480b-a35b-instruct"
    "qwen/qwen2.5-coder-32b-instruct"
    "qwen/qwen3.5-397b-a17b"
    "mistralai/devstral-2-123b-instruct-2512"
    "mistralai/mistral-large-3-675b-instruct-2512"
    "meta/llama-3.1-405b-instruct"
)

# Select models based on group
if [ "$MODEL_GROUP" = "group1" ]; then
    MODELS=("${GROUP1_MODELS[@]}")
    OUTPUT_FILE="results-group1.json"
elif [ "$MODEL_GROUP" = "group2" ]; then
    MODELS=("${GROUP2_MODELS[@]}")
    OUTPUT_FILE="results-group2.json"
else
    MODELS=("${ALL_MODELS[@]}")
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
RESULTS_JSON=$(cat <<EOF
{
  "timestamp": "$TIMESTAMP",
  "prompt": "$PROMPT",
  "models": []
}
EOF
)

echo -e "${YELLOW}Starting NVIDIA NIM Model Benchmarks${MODEL_GROUP:+ (Group: $MODEL_GROUP)}...${NC}"
echo "Timestamp: $TIMESTAMP"
echo "Testing ${#MODELS[@]} models..."
echo ""

if [ -z "$API_KEY" ]; then
    echo -e "${RED}Error: NIM_API_KEY environment variable not set${NC}"
    exit 1
fi

RESULTS=()
for model in "${MODELS[@]}"; do
    echo -e "${YELLOW}Testing: $model${NC}"

    START_TIME=$(date +%s%N)

    RESPONSE=$(curl -s -X POST \
        "$API_BASE/chat/completions" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$model\",
            \"messages\": [
                {
                    \"role\": \"user\",
                    \"content\": \"$PROMPT\"
                }
            ],
            \"temperature\": 0.7,
            \"top_p\": 0.9,
            \"max_tokens\": 500,
            \"stream\": false
        }" 2>&1)

    END_TIME=$(date +%s%N)
    RESPONSE_TIME=$((($END_TIME - $START_TIME) / 1000000))

    ERROR=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('error', {}).get('message', ''))" 2>/dev/null || echo "")
    if [ -n "$ERROR" ]; then
        echo -e "${RED}  ✗ Failed: $ERROR${NC}"
        MODEL_RESULT=$(cat <<EOF
{
  "model": "$model",
  "success": false,
  "error": "$ERROR",
  "responseTime": null,
  "tokensGenerated": null,
  "totalTokens": null,
  "response": null
}
EOF
)
    else
        CONTENT=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('choices', [{}])[0].get('message', {}).get('content', ''))" 2>/dev/null || echo "")
        TOKENS_GENERATED=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('usage', {}).get('completion_tokens', 0))" 2>/dev/null || echo "0")
        TOTAL_TOKENS=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('usage', {}).get('total_tokens', 0))" 2>/dev/null || echo "0")

        if [ -z "$CONTENT" ]; then
            ERROR="No content in response"
            echo -e "${RED}  ✗ Failed: $ERROR${NC}"
            MODEL_RESULT=$(cat <<EOF
{
  "model": "$model",
  "success": false,
  "error": "$ERROR",
  "responseTime": null,
  "tokensGenerated": null,
  "totalTokens": null,
  "response": null
}
EOF
)
        else
            echo -e "${GREEN}  ✓ Success (${RESPONSE_TIME}ms, $TOKENS_GENERATED tokens)${NC}"

            CONTENT_ESCAPED=$(echo "$CONTENT" | python3 -c "import sys, json; print(json.dumps(sys.stdin.read()))")

            MODEL_RESULT=$(cat <<EOF
{
  "model": "$model",
  "success": true,
  "responseTime": $RESPONSE_TIME,
  "tokensGenerated": $TOKENS_GENERATED,
  "totalTokens": $TOTAL_TOKENS,
  "response": $CONTENT_ESCAPED,
  "error": null
}
EOF
)
        fi
    fi

    RESULTS+=("$MODEL_RESULT")
    sleep 0.5
done

echo ""
echo -e "${YELLOW}Compiling results...${NC}"

MODELS_JSON=$(python3 << 'PYSCRIPT'
import sys
import json

results = []
for line in sys.stdin:
    line = line.strip()
    if line:
        try:
            results.append(json.loads(line))
        except:
            pass

print(json.dumps(results))
PYSCRIPT
)

# Read results from piped input
MODELS_JSON="["
first=true
for result in "${RESULTS[@]}"; do
    if [ "$first" = true ]; then
        MODELS_JSON="$MODELS_JSON$result"
        first=false
    else
        MODELS_JSON="$MODELS_JSON,$result"
    fi
done
MODELS_JSON="$MODELS_JSON]"

# Merge with timestamp and prompt
FINAL_JSON=$(python3 << 'PYSCRIPT'
import json
import sys

timestamp = """$TIMESTAMP"""
prompt = """$PROMPT"""
models = $MODELS_JSON

success_count = sum(1 for m in models if m.get('success'))
total_count = len(models)
fastest_model = "N/A"
fastest_time = 0

successful = [m for m in models if m.get('success')]
if successful:
    fastest = min(successful, key=lambda x: x.get('responseTime', float('inf')))
    fastest_model = fastest.get('model', 'N/A')
    fastest_time = fastest.get('responseTime', 0)

result = {
    "timestamp": timestamp,
    "prompt": prompt,
    "models": models,
    "summary": {
        "successCount": success_count,
        "totalModels": total_count,
        "fastestModel": fastest_model,
        "fastestTime": fastest_time
    }
}

print(json.dumps(result, indent=2))
PYSCRIPT
)

echo "$FINAL_JSON" > "$OUTPUT_FILE"

echo -e "${GREEN}Results saved to $OUTPUT_FILE${NC}"
SUCCESS_COUNT=$(echo "$FINAL_JSON" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('summary', {}).get('successCount', 0))")
TOTAL_COUNT=$(echo "$FINAL_JSON" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('summary', {}).get('totalModels', 0))")
echo "Summary: $SUCCESS_COUNT/$TOTAL_COUNT successful"

# Only update history for full runs (not parallel groups)
if [ "$MODEL_GROUP" = "all" ] || [ -z "$MODEL_GROUP" ]; then
    if [ -f "$HISTORY_FILE" ]; then
        python3 << PYSCRIPT
import json

with open("$HISTORY_FILE", "r") as f:
    history = json.load(f)

with open("$OUTPUT_FILE", "r") as f:
    new_run = json.load(f)

history['runs'].insert(0, new_run)
history['runs'] = history['runs'][:720]

with open("$HISTORY_FILE", "w") as f:
    json.dump(history, f, indent=2)
PYSCRIPT
    else
        python3 << PYSCRIPT
import json

with open("$OUTPUT_FILE", "r") as f:
    new_run = json.load(f)

history = {"runs": [new_run]}

with open("$HISTORY_FILE", "w") as f:
    json.dump(history, f, indent=2)
PYSCRIPT
    fi
    echo -e "${GREEN}History updated: $HISTORY_FILE${NC}"
fi
