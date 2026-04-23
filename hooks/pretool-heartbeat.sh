#!/bin/bash
# Emits a lightweight "activity" event for every tool call so the dashboard
# can show Claude is still alive. Best-effort — failures never block the
# pipeline. Only fires when a generation is active (autonoma/.generation-id
# exists) and the Autonoma API is reachable.

set -u

INPUT=$(cat)

# Guard: only fire during an active generation.
GENERATION_ID=$(cat autonoma/.generation-id 2>/dev/null || echo '')
[ -z "$GENERATION_ID" ] && exit 0
[ -z "${AUTONOMA_API_URL:-}" ] && exit 0
[ -z "${AUTONOMA_API_KEY:-}" ] && exit 0

# ---------------------------------------------------------------------------
# Streamer liveness check + auto-revive. If the transcript streamer daemon
# has died (crash, OS restart, etc.) re-launch it so the dashboard keeps
# receiving events. kill -0 is nearly free when the process is alive.
# Skipped when the plugin's streamer.py is missing (e.g. older plugin cache).
# ---------------------------------------------------------------------------
STREAMER_PID_FILE="autonoma/.streamer.pid"
STREAMER_LOG="autonoma/.streamer.log"
STREAMER_SCRIPT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")/..}/hooks/transcript-streamer.py"

streamer_alive() {
  [ -s "$STREAMER_PID_FILE" ] || return 1
  local pid
  pid=$(cat "$STREAMER_PID_FILE" 2>/dev/null)
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

if ! streamer_alive && [ -f "$STREAMER_SCRIPT" ]; then
  TRANSCRIPT_PATH=$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('transcript_path',''))" 2>/dev/null || echo '')
  if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ]; then
    nohup python3 "$STREAMER_SCRIPT" \
      "$TRANSCRIPT_PATH" \
      "$GENERATION_ID" \
      "$AUTONOMA_API_URL" \
      "$AUTONOMA_API_KEY" \
      >> "$STREAMER_LOG" 2>&1 </dev/null &
    NEW_PID=$!
    echo "$NEW_PID" > "$STREAMER_PID_FILE"
    disown "$NEW_PID" 2>/dev/null || true
    echo "[$(date +%H:%M:%S)] streamer revived by pretool-heartbeat pid=$NEW_PID transcript=$TRANSCRIPT_PATH" >> "$STREAMER_LOG"
  fi
fi

# Build the payload: tool name + a short preview of the most informative arg.
# Heavy args (full file contents from Write/Edit) are never forwarded.
PAYLOAD=$(printf '%s' "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
tool = data.get('tool_name') or ''
if not tool:
    sys.exit(0)
inp = data.get('tool_input') or {}
# Pick the first informative string field; never forward large blobs.
preview = ''
for key in ('command', 'description', 'file_path', 'pattern', 'path', 'query', 'prompt', 'url'):
    v = inp.get(key)
    if isinstance(v, str) and v.strip():
        preview = v.replace('\n', ' ').strip()[:200]
        break
print(json.dumps({'type': 'activity', 'data': {'tool': tool, 'preview': preview}}))
" 2>/dev/null)

[ -z "$PAYLOAD" ] && exit 0

# Short timeout — the hook runs before every tool call, never block the session.
curl --max-time 2 -sf -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" >/dev/null 2>&1 || true

exit 0
