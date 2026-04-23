#!/bin/bash
# UserPromptSubmit hook. Fires on every user prompt, early-exits unless:
#   1. The prompt invokes the generate-tests skill/command, AND
#   2. The pipeline has not already been kicked off (no autonoma/.generation-id).
#
# When both conditions hold, this script owns pipeline startup so the agent
# never has to remember to do it:
#   - verifies required env vars (hard-fails if AUTONOMA_DOCS_URL is unset)
#   - creates autonoma/ output dirs
#   - writes autonoma/.docs-url
#   - POSTs /v1/setup/setups to create the generation record
#   - writes autonoma/.generation-id
#   - emits step.started for step 0
#
# Exit 0 always (best-effort reporting must never block test generation).

set -u

INPUT=$(cat)

PROMPT=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))" 2>/dev/null || echo '')

# Match either the slash command or a direct mention of the skill name
case "$PROMPT" in
  */generate-tests*|*generate-tests*) ;;
  *) exit 0 ;;
esac

# Idempotency: if we've already kicked off this project's pipeline, nothing to do.
if [ -s autonoma/.generation-id ]; then
  exit 0
fi

# Hard-require AUTONOMA_DOCS_URL — the plugin refuses to guess a docs URL.
if [ -z "${AUTONOMA_DOCS_URL:-}" ]; then
  echo "[autonoma pipeline-kickoff] ERROR: AUTONOMA_DOCS_URL is not set." >&2
  echo "[autonoma pipeline-kickoff] Re-launch Claude using the onboarding command from the Autonoma dashboard (it exports AUTONOMA_DOCS_URL), or export it manually before running /generate-tests." >&2
  exit 0
fi

mkdir -p autonoma/skills autonoma/qa-tests
echo "$AUTONOMA_DOCS_URL" > autonoma/.docs-url

# Nothing below this line should ever fail hard — we must not block the agent.
if [ -z "${AUTONOMA_API_URL:-}" ] || [ -z "${AUTONOMA_API_KEY:-}" ] || [ -z "${AUTONOMA_PROJECT_ID:-}" ]; then
  echo "[autonoma pipeline-kickoff] WARN: AUTONOMA_API_URL/AUTONOMA_API_KEY/AUTONOMA_PROJECT_ID not all set. Skipping dashboard reporting." >&2
  exit 0
fi

# Derive a human-readable app name from the project dir (best-effort).
APP_NAME=$(basename "$(pwd)")

RESPONSE=$(curl -sf -X POST "${AUTONOMA_API_URL}/v1/setup/setups" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"applicationId\":\"${AUTONOMA_PROJECT_ID}\",\"repoName\":\"${APP_NAME}\"}" 2>/dev/null || echo '{}')

GENERATION_ID=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo '')

if [ -z "$GENERATION_ID" ]; then
  echo "[autonoma pipeline-kickoff] WARN: setup creation returned no id. Dashboard will not reflect this run." >&2
  exit 0
fi

echo "$GENERATION_ID" > autonoma/.generation-id
echo "[autonoma pipeline-kickoff] Pipeline kickoff complete. generation_id=${GENERATION_ID}" >&2

curl -sf -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"step.started","data":{"step":0,"name":"Knowledge Base"}}' >/dev/null 2>&1 || true

touch autonoma/.step-0-started

# ---------------------------------------------------------------------------
# Launch the transcript streamer as a detached background daemon. It tails
# the session JSONL and forwards assistant text/thinking/tool-use/tool-result
# events to /v1/setup/setups/{id}/events so the dashboard can render a live
# activity log. Best-effort, never blocks.
# ---------------------------------------------------------------------------
TRANSCRIPT_PATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('transcript_path',''))" 2>/dev/null || echo '')

if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ]; then
  STREAMER_PID_FILE="autonoma/.streamer.pid"
  STREAMER_LOG="autonoma/.streamer.log"
  STREAMER_SCRIPT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")/..}/hooks/transcript-streamer.py"

  # If a prior streamer is still alive (e.g. from a previous session in this
  # project dir), replace it — the transcript path has changed.
  if [ -s "$STREAMER_PID_FILE" ]; then
    existing_pid=$(cat "$STREAMER_PID_FILE" 2>/dev/null || echo '')
    if [ -n "$existing_pid" ] && kill -0 "$existing_pid" 2>/dev/null; then
      kill "$existing_pid" 2>/dev/null || true
    fi
  fi

  if [ -f "$STREAMER_SCRIPT" ]; then
    nohup python3 "$STREAMER_SCRIPT" \
      "$TRANSCRIPT_PATH" \
      "$GENERATION_ID" \
      "$AUTONOMA_API_URL" \
      "$AUTONOMA_API_KEY" \
      >> "$STREAMER_LOG" 2>&1 </dev/null &
    STREAMER_PID=$!
    echo "$STREAMER_PID" > "$STREAMER_PID_FILE"
    disown "$STREAMER_PID" 2>/dev/null || true
    echo "[autonoma pipeline-kickoff] Transcript streamer started. pid=${STREAMER_PID} transcript=${TRANSCRIPT_PATH}" >&2
  fi
fi

exit 0
