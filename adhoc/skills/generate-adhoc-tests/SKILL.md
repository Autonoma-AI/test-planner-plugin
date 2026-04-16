---
name: generate-adhoc-tests
description: >
  Generates focused E2E test cases for a user-defined topic or feature area through a validated
  pipeline. Accepts a focus description (e.g. "signatures and documents", "invoice edge cases")
  and produces tests scoped to that domain. Reads existing knowledge base and scenarios if
  available; falls back to a targeted codebase scan if not.
---

# Autonoma Ad Hoc Test Generation Pipeline

You are orchestrating a focused test generation pipeline. The user has requested tests for a
specific topic or feature area. You will resolve the focus, load context, spawn an isolated
subagent to generate tests, and validate the output.

**Every step MUST complete successfully and pass validation before proceeding.**
Do NOT skip steps. Do NOT proceed if validation fails.

## User Confirmation

By default, after the test generation step, you MUST present the summary and ask the user for
confirmation using the `AskUserQuestion` tool before uploading.

**Auto-advance mode:** If `AUTONOMA_AUTO_ADVANCE` is set to `true`, skip the confirmation prompt
and proceed directly to upload after presenting the summary.

## Before Starting

Save the project root (subagents change working directory, so we need an absolute path reference):
```bash
AUTONOMA_ROOT="$(pwd)"
echo "$AUTONOMA_ROOT" > /tmp/autonoma-project-root
mkdir -p autonoma/qa-tests
```

Read the environment variables:
- `AUTONOMA_API_KEY` — your Autonoma API key
- `AUTONOMA_PROJECT_ID` — your Autonoma project ID
- `AUTONOMA_API_URL` — Autonoma API base URL
- `AUTONOMA_AUTO_ADVANCE` — (optional) set to `true` to skip confirmation prompt

Derive a clean human-readable application name:
```bash
APP_NAME=$(git remote get-url origin 2>/dev/null | sed 's/.*\///' | sed 's/\.git//' || basename "$(pwd)")
```

Create the generation record so the dashboard can track progress:
```bash
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "${AUTONOMA_API_URL}/v1/setup/setups" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"applicationId\":\"${AUTONOMA_PROJECT_ID}\",\"repoName\":\"${APP_NAME}\"}")
HTTP_STATUS=$(echo "$RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')
echo "Setup API response (HTTP $HTTP_STATUS): $BODY"
GENERATION_ID=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo '')
mkdir -p autonoma
echo "$GENERATION_ID" > autonoma/.generation-id
echo "Generation ID: $GENERATION_ID"
```

If `GENERATION_ID` is empty, log it for debugging and continue — reporting is best-effort.

## Step 1: Resolve Focus Prompt

Read the user's input. The text after the skill name is the focus description.

**If a focus description was provided**, use it directly. Derive `FOCUS_SLUG`:
```bash
FOCUS_PROMPT="<the user's description>"
FOCUS_SLUG=$(echo "$FOCUS_PROMPT" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-\|-$//g')
echo "Focus: $FOCUS_PROMPT"
echo "Slug: $FOCUS_SLUG"
```

**If no focus description was provided**, check available context and suggest focus areas:
1. Read `autonoma/AUTONOMA.md` for `core_flows` if it exists
2. Otherwise list top-level route/feature files in the codebase
3. Call `AskUserQuestion` with 3–4 suggested focus areas drawn from what you found, plus an "Other"
   option so the user can describe their own
4. Wait for the user's response, then derive `FOCUS_SLUG` from their answer

## Step 2: Load Context

Report step start:
```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
GENERATION_ID=$(cat "$AUTONOMA_ROOT/autonoma/.generation-id" 2>/dev/null || echo '')
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"step.started","data":{"step":0,"name":"Context"}}' || true
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"log","data":{"message":"Loading codebase context for focused test generation..."}}' || true
```

Prefer existing main-planner outputs; fall back to a targeted codebase scan if they are absent:

```
if autonoma/AUTONOMA.md exists → read it; extract core_flows, feature_count, app_name
if autonoma/scenarios.md exists → read it; extract scenario names, entity_types, variable_fields
if autonoma/skills/ exists → list all .md files in that directory
if autonoma/qa-tests/ exists → list all existing test files (title + path) to avoid duplication
else → scan the codebase for routes, pages, and features relevant to FOCUS_PROMPT
```

Compile an `EXISTING_TESTS` summary: a flat list of "folder/filename: title" for every test that
already exists under `autonoma/qa-tests/`. This will be passed to the subagent.

Report step complete:
```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
GENERATION_ID=$(cat "$AUTONOMA_ROOT/autonoma/.generation-id" 2>/dev/null || echo '')
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"step.completed","data":{"step":0,"name":"Context"}}' || true
```

## Step 3: Generate Focused Tests

Report step start:
```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
GENERATION_ID=$(cat "$AUTONOMA_ROOT/autonoma/.generation-id" 2>/dev/null || echo '')
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"step.started","data":{"step":1,"name":"Focused Tests"}}' || true
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"log\",\"data\":{\"message\":\"Generating focused E2E tests for: ${FOCUS_PROMPT}\"}}" || true
```

Spawn the `focused-test-case-generator` subagent with the following task (substitute actual values
for `FOCUS_PROMPT`, `FOCUS_SLUG`, and the loaded context before spawning):

> **FOCUS_PROMPT**: <the user's focus description>
> **FOCUS_SLUG**: <kebab-case slug>
>
> Generate E2E test cases focused exclusively on the topic described in FOCUS_PROMPT.
> Write tests to `autonoma/qa-tests/{FOCUS_SLUG}/`.
>
> Context available (use what exists, skip what doesn't):
> - Knowledge base: `autonoma/AUTONOMA.md` (core_flows: <list>, feature_count: <n>)
> - Scenarios: `autonoma/scenarios.md` (scenarios: <list>, variable_fields: <list>)
> - Skills: `autonoma/skills/` (<n> files)
>
> EXISTING_TESTS (do not duplicate these):
> <flat list of existing test paths and titles>
>
> You MUST create `autonoma/qa-tests/{FOCUS_SLUG}/INDEX.md` with frontmatter containing
> total_tests, total_folders, folder breakdown, and coverage_correlation.
> Each test file MUST have frontmatter with title, description, criticality, scenario, and flow.
> Write INDEX.md FIRST, then individual test files.
> Fetch the latest instructions from https://docs.agent.autonoma.app/llms/test-planner/step-3-e2e-tests.txt first.

**After the subagent completes:**
1. Verify `autonoma/qa-tests/{FOCUS_SLUG}/INDEX.md` exists and is non-empty
2. The PostToolUse hook will have validated the INDEX frontmatter and individual test file frontmatter
3. Read the INDEX.md and present the summary to the user — total tests, folder breakdown, coverage correlation

Report step complete and upload test cases:
```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
GENERATION_ID=$(cat "$AUTONOMA_ROOT/autonoma/.generation-id" 2>/dev/null || echo '')
TEST_COUNT=$(find "$AUTONOMA_ROOT/autonoma/qa-tests/${FOCUS_SLUG}" -name '*.md' ! -name 'INDEX.md' 2>/dev/null | wc -l | tr -d ' ')
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"log\",\"data\":{\"message\":\"Generated ${TEST_COUNT} focused tests for '${FOCUS_PROMPT}'. Preparing upload...\"}}" || true
```

**If `AUTONOMA_AUTO_ADVANCE` is not `true`:** Call `AskUserQuestion` with:
- question: "Do these focused tests look correct for your requested topic?"
- options: ["Yes, upload to dashboard", "I want to suggest changes"]
Wait for the user's response before uploading.
**If `AUTONOMA_AUTO_ADVANCE=true`:** Skip the prompt and proceed directly to upload.

```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
GENERATION_ID=$(cat "$AUTONOMA_ROOT/autonoma/.generation-id" 2>/dev/null || echo '')
[ -n "$GENERATION_ID" ] && python3 -c "
import os, json
proj_root = open('/tmp/autonoma-project-root').read().strip() if os.path.exists('/tmp/autonoma-project-root') else '.'
qa_dir = os.path.join(proj_root, 'autonoma/qa-tests/${FOCUS_SLUG}')
test_cases = []
for root, dirs, files in os.walk(qa_dir):
    for f in files:
        if f.endswith('.md') and f != 'INDEX.md':
            path = os.path.join(root, f)
            folder = os.path.relpath(root, qa_dir)
            with open(path) as fh:
                content = fh.read()
            entry = {'name': f, 'content': content}
            if folder != '.':
                entry['folder'] = '${FOCUS_SLUG}/' + folder
            test_cases.append(entry)
print(json.dumps({'testCases': test_cases}))
" | curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/artifacts" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @- || true

[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"step.completed","data":{"step":1,"name":"Focused Tests"}}' || true
```

## Completion

After all steps complete, summarize:
- **Focus**: The topic tested and the focus slug used as the output folder
- **Tests generated**: Total count, folder breakdown, coverage correlation
- **Context used**: Whether AUTONOMA.md and scenarios.md were available or a codebase scan was used
- **Output location**: `autonoma/qa-tests/{FOCUS_SLUG}/`
- **Avoided duplicates**: How many existing tests were found and respected
