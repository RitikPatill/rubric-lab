#!/usr/bin/env bash
# record_demo.sh -- drive the RubricLab demo: two runs with a prompt tweak between them,
# produce diff URL, and capture screenshots.
set -euo pipefail

# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set. Export it before running this script." >&2
  exit 1
fi

if ! command -v docker &>/dev/null; then
  echo "ERROR: docker is not installed or not in PATH." >&2
  exit 1
fi

# Ensure docker compose (v2 plugin) is available
if ! docker compose version &>/dev/null; then
  echo "ERROR: 'docker compose' (v2) is not available. Please install the Docker Compose plugin." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

API_URL="http://localhost:8000"
WEB_URL="http://localhost:3000"

wait_for_api() {
  local attempts=0
  local max=60
  echo "Waiting for API to be ready..."
  while ! curl -sf "${API_URL}/health" >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if [[ $attempts -ge $max ]]; then
      echo "ERROR: API did not become healthy after $((max * 2))s." >&2
      exit 1
    fi
    sleep 2
  done
  echo "  API is healthy."
}

wait_for_run() {
  local run_id=$1
  local attempts=0
  local max=120  # 6 minutes max
  echo "Waiting for run ${run_id} to complete..."
  while true; do
    local status
    status=$(curl -sf "${API_URL}/runs/${run_id}" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
    if [[ "$status" == "done" || "$status" == "failed" ]]; then
      echo "  Run ${run_id} finished with status: ${status}"
      break
    fi
    attempts=$((attempts + 1))
    if [[ $attempts -ge $max ]]; then
      echo "ERROR: Run ${run_id} did not complete in time." >&2
      exit 1
    fi
    sleep 3
  done
}

take_screenshot() {
  local url=$1
  local out=$2
  mkdir -p docs
  if command -v npx &>/dev/null; then
    if npx --yes playwright screenshot --browser chromium "$url" "$out" 2>/dev/null; then
      echo "  Screenshot saved: $out"
      return 0
    fi
  fi
  echo "  -> No headless browser available. Open $url and save screenshot to $out"
}

# ---------------------------------------------------------------------------
# Step 1: Start services
# ---------------------------------------------------------------------------

echo "==> Building and starting services..."
docker compose up -d --build

# ---------------------------------------------------------------------------
# Step 2: Wait for API
# ---------------------------------------------------------------------------

wait_for_api

# ---------------------------------------------------------------------------
# Step 3: Get demo suite ID
# ---------------------------------------------------------------------------

echo "==> Fetching demo suite..."
# All JSON parsing uses stdin piping (no shell-variable expansion inside python -c strings) — quoting is already safe.
SUITE_ID=$(curl -sf "${API_URL}/suites" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
echo "  Suite ID: ${SUITE_ID}"

# ---------------------------------------------------------------------------
# Step 4: Trigger run 1
# ---------------------------------------------------------------------------

echo "==> Triggering run 1..."
RUN1_ID=$(curl -sf -X POST "${API_URL}/runs"   -H "Content-Type: application/json"   -d "{\"suite_id\": \"${SUITE_ID}\"}"   | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Run 1 ID: ${RUN1_ID}"

# ---------------------------------------------------------------------------
# Step 5: Poll run 1 until done
# ---------------------------------------------------------------------------

wait_for_run "${RUN1_ID}"

# ---------------------------------------------------------------------------
# Step 6: Screenshot after run 1
# ---------------------------------------------------------------------------

take_screenshot "${WEB_URL}/suites/${SUITE_ID}"   "docs/screenshot-suite.png"
take_screenshot "${WEB_URL}/runs/${RUN1_ID}"       "docs/screenshot-run.png"

# ---------------------------------------------------------------------------
# Step 7: Tweak the system prompt (simulates a developer improving the agent)
# ---------------------------------------------------------------------------

PROMPT_FILE="agents/research/prompt.md"
echo "==> Tweaking system prompt in ${PROMPT_FILE}..."
python3 - << 'INNER'
import pathlib
p = pathlib.Path("agents/research/prompt.md")
text = p.read_text(encoding="utf-8").rstrip()
if "Always cite your sources." not in text:
    text += " Always cite your sources."
p.write_text(text + "
", encoding="utf-8")
print("  Prompt updated.")
INNER

echo "==> Restarting API container to pick up new prompt..."
docker compose restart api
wait_for_api

# ---------------------------------------------------------------------------
# Step 8: Trigger run 2
# ---------------------------------------------------------------------------

echo "==> Triggering run 2..."
RUN2_ID=$(curl -sf -X POST "${API_URL}/runs"   -H "Content-Type: application/json"   -d "{\"suite_id\": \"${SUITE_ID}\"}"   | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Run 2 ID: ${RUN2_ID}"

# ---------------------------------------------------------------------------
# Step 9: Poll run 2 until done
# ---------------------------------------------------------------------------

wait_for_run "${RUN2_ID}"

# ---------------------------------------------------------------------------
# Step 10: Screenshot diff view
# ---------------------------------------------------------------------------

take_screenshot "${WEB_URL}/diff/${RUN1_ID}/${RUN2_ID}" "docs/screenshot-diff.png"

# ---------------------------------------------------------------------------
# Step 11: Summary
# ---------------------------------------------------------------------------

echo ""
echo "============================================================"
echo " RubricLab demo complete!"
echo "============================================================"
echo "  Suite:    ${WEB_URL}/suites/${SUITE_ID}"
echo "  Run 1:    ${WEB_URL}/runs/${RUN1_ID}"
echo "  Run 2:    ${WEB_URL}/runs/${RUN2_ID}"
echo "  Diff:     ${WEB_URL}/diff/${RUN1_ID}/${RUN2_ID}"
echo "  API diff: ${API_URL}/diff?run_a=${RUN1_ID}&run_b=${RUN2_ID}"
echo ""
echo "  Screenshots: docs/screenshot-suite.png  docs/screenshot-run.png  docs/screenshot-diff.png"
echo "============================================================"
