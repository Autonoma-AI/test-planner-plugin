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
