---
name: generate-tests
description: >
  Generates E2E test cases for a codebase through a validated multi-step pipeline.
  Each step runs in an isolated subagent and must pass deterministic validation
  before the next step begins. Use when the user wants to generate tests, create
  test scenarios, or build a test suite for their project.
---

# Autonoma E2E Test Generation Pipeline

You are orchestrating a 5-step test generation pipeline. Each step runs as an isolated subagent.
**Every step MUST complete successfully and pass validation before the next step begins.**
Do NOT skip steps. Do NOT proceed if validation fails.

## User Confirmation Between Steps

By default, after each step (1, 2, 3, and 4), present the summary and automatically proceed to the
next step once validation passes.

**Manual confirmation mode:** If the environment variable `AUTONOMA_REQUIRE_CONFIRMATION` is set to
`true`, you MUST present the summary and then ask the user for confirmation using the
`AskUserQuestion` tool.

After calling `AskUserQuestion`, wait for the user's response.
Only proceed to the next step after they confirm.

## Before Starting

Create the output directory and save the project root:

```bash
AUTONOMA_ROOT="$(pwd)"
echo "$AUTONOMA_ROOT" > /tmp/autonoma-project-root
mkdir -p autonoma autonoma/skills autonoma/qa-tests
cleanup_dev_server() {
  DEV_SERVER_PID=$(cat /tmp/autonoma-dev-server-pid 2>/dev/null || echo '')
  if [ -n "$DEV_SERVER_PID" ]; then
    kill "$DEV_SERVER_PID" 2>/dev/null || true
    rm -f /tmp/autonoma-dev-server-pid
    echo "Dev server (PID $DEV_SERVER_PID) stopped."
  fi
}
```

The plugin root path is persisted to `/tmp/autonoma-plugin-root` automatically by the PostToolUse hook on the first Write:

```bash
PLUGIN_ROOT=$(cat /tmp/autonoma-plugin-root 2>/dev/null || echo '')
```

Read the environment variables required for reporting progress back to Autonoma:
- `AUTONOMA_API_KEY`
- `AUTONOMA_PROJECT_ID`
- `AUTONOMA_API_URL`
- `AUTONOMA_REQUIRE_CONFIRMATION` — optional

Prepare the SDK reference repo for Step 1:

```bash
SDK_REF_DIR="${AUTONOMA_SDK_REF_DIR:-}"
if [ -n "$SDK_REF_DIR" ] && [ -d "$SDK_REF_DIR" ]; then
  echo "$SDK_REF_DIR" > /tmp/autonoma-sdk-ref-dir
else
  SDK_REF_DIR="$(mktemp -d)/autonoma-sdk"
  if git clone --depth 1 https://github.com/Autonoma-AI/sdk.git "$SDK_REF_DIR"; then
    echo "$SDK_REF_DIR" > /tmp/autonoma-sdk-ref-dir
  else
    echo "ERROR: Unable to prepare the SDK reference repo."
    cleanup_dev_server
    exit 1
  fi
fi
```

Before creating the record, derive a clean human-readable application name from the repository. Look at the git remote URL, the directory name, and any `package.json` / `pyproject.toml` / `README.md` to infer what the product is actually called. Prefer the product name over the repo slug.

Create the generation record so the dashboard can track progress in real time:

```bash
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "${AUTONOMA_API_URL}/v1/setup/setups" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"applicationId\":\"${AUTONOMA_PROJECT_ID}\",\"repoName\":\"${APP_NAME}\"}")
HTTP_STATUS=$(echo "$RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')
echo "Setup API response (HTTP $HTTP_STATUS): $BODY"
GENERATION_ID=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo '')
echo "$GENERATION_ID" > autonoma/.generation-id
echo "Generation ID: $GENERATION_ID"
```

If `GENERATION_ID` is empty, log the HTTP status and response body above for debugging, then continue anyway.

## Step 1: SDK Integration

Report step start:

```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
GENERATION_ID=$(cat "$AUTONOMA_ROOT/autonoma/.generation-id" 2>/dev/null || echo '')
SDK_REF_DIR=$(cat /tmp/autonoma-sdk-ref-dir 2>/dev/null || echo '')
echo "GENERATION_ID=${GENERATION_ID:-<empty>}"
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"step.started","data":{"step":0,"name":"SDK Integration"}}' || true
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"log","data":{"message":"Detecting stack and integrating the Autonoma SDK..."}}' || true
```

Spawn the `sdk-integrator` subagent with the following task:

> Read the SDK reference repo path from `/tmp/autonoma-sdk-ref-dir` and use it as read-only context.
> Detect the project stack, map it against the supported SDK docs matrix, and stop immediately with
> a `mailto:support@autonoma.app` link if unsupported.
> Create a branch, install the SDK from package managers only, implement the SDK endpoint following
> the matching example or README pattern, ensure `AUTONOMA_SHARED_SECRET` and `AUTONOMA_SIGNING_SECRET`
> exist in `.env`, update `.env.example`, keep `autonoma/` out of commits, start or reuse a dev server,
> verify signed `discover`, `up`, and `down`, write `autonoma/.sdk-endpoint`, commit with
> `feat: integrate autonoma sdk`, and create a PR if `gh` is available.
> Do NOT modify the SDK source repo. Do NOT modify database schemas, migrations, or models.

**After the subagent completes:**
1. Verify `autonoma/.sdk-endpoint` exists and is non-empty
2. Read and export `AUTONOMA_SDK_ENDPOINT` from that file
3. Read `AUTONOMA_SHARED_SECRET` and `AUTONOMA_SIGNING_SECRET` from `.env`
4. Confirm the endpoint is reachable with a signed `discover` request
5. Retain `/tmp/autonoma-dev-server-pid` for cleanup after the pipeline finishes
6. Present the summary to the user — detected stack, packages installed, endpoint URL, PR URL if available

Load the endpoint and secrets:

```bash
AUTONOMA_SDK_ENDPOINT=$(tr -d '\n' < "$AUTONOMA_ROOT/autonoma/.sdk-endpoint" 2>/dev/null || echo '')
AUTONOMA_SHARED_SECRET=$(grep '^AUTONOMA_SHARED_SECRET=' "$AUTONOMA_ROOT/.env" 2>/dev/null | tail -n 1 | cut -d= -f2-)
AUTONOMA_SIGNING_SECRET=$(grep '^AUTONOMA_SIGNING_SECRET=' "$AUTONOMA_ROOT/.env" 2>/dev/null | tail -n 1 | cut -d= -f2-)
export AUTONOMA_SDK_ENDPOINT AUTONOMA_SHARED_SECRET AUTONOMA_SIGNING_SECRET

if [ -z "$AUTONOMA_SDK_ENDPOINT" ] || [ -z "$AUTONOMA_SHARED_SECRET" ]; then
  echo "ERROR: Step 1 did not produce a usable SDK endpoint and shared secret."
  cleanup_dev_server
  exit 1
fi

BODY='{"action":"discover"}'
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$AUTONOMA_SHARED_SECRET" | sed 's/.*= //')
HTTP_STATUS=$(curl -sS -o /tmp/autonoma-sdk-discover-check.json -w "%{http_code}" -X POST "$AUTONOMA_SDK_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "x-signature: $SIG" \
  -d "$BODY")
if [ "$HTTP_STATUS" != "200" ]; then
  echo "ERROR: SDK discover check failed after Step 1 (HTTP $HTTP_STATUS)."
  cleanup_dev_server
  exit 1
fi
```

Report step complete:

```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
GENERATION_ID=$(cat "$AUTONOMA_ROOT/autonoma/.generation-id" 2>/dev/null || echo '')
echo "GENERATION_ID=${GENERATION_ID:-<empty>}"
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"step.completed","data":{"step":0,"name":"SDK Integration"}}' || true
```

7. **If `AUTONOMA_REQUIRE_CONFIRMATION=true`:** Call `AskUserQuestion` with:
   - question: "Does this SDK integration summary look correct? The next step will use the endpoint produced here."
   - options: ["Yes, proceed to Step 2", "I want to suggest changes"]
   Wait for the user's response before proceeding.
   **Otherwise:** Skip the prompt and proceed directly to Step 2.

## Step 2: Generate Knowledge Base

Report step start:

```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
GENERATION_ID=$(cat "$AUTONOMA_ROOT/autonoma/.generation-id" 2>/dev/null || echo '')
echo "GENERATION_ID=${GENERATION_ID:-<empty>}"
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"step.started","data":{"step":1,"name":"Knowledge Base"}}' || true
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"log","data":{"message":"Analyzing codebase structure and identifying features..."}}' || true
```

Spawn the `kb-generator` subagent with the following task:

> Analyze the codebase and generate the knowledge base. Write the output to `autonoma/AUTONOMA.md`
> and create skill files in `autonoma/skills/`. The file MUST have YAML frontmatter with
> app_name, app_description, core_flows (feature/description/core table), feature_count, and skill_count.
> You MUST also write `autonoma/features.json` — a machine-readable inventory of every feature discovered.
> It must have: features array (each with name, type, path, core), total_features, total_routes, total_api_routes.
> Fetch the latest instructions from https://docs.agent.autonoma.app/llms/test-planner/step-1-knowledge-base.txt first.

**After the subagent completes:**
1. Verify `autonoma/AUTONOMA.md` and `autonoma/features.json` exist and are non-empty
2. The PostToolUse hook will have validated the frontmatter and features.json schema automatically
3. Read the file and present the frontmatter to the user — specifically the core_flows table

Report step complete and upload skills:

```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
GENERATION_ID=$(cat "$AUTONOMA_ROOT/autonoma/.generation-id" 2>/dev/null || echo '')
echo "GENERATION_ID=${GENERATION_ID:-<empty>}"
SKILL_COUNT=$(ls "$AUTONOMA_ROOT/autonoma/skills/"*.md 2>/dev/null | wc -l | tr -d ' ')
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"log\",\"data\":{\"message\":\"Knowledge base complete. Generated ${SKILL_COUNT} skills. Uploading to dashboard...\"}}" || true
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"step.completed","data":{"step":1,"name":"Knowledge Base"}}' || true
[ -n "$GENERATION_ID" ] && python3 -c "
import os, json
root = open('/tmp/autonoma-project-root').read().strip() if os.path.exists('/tmp/autonoma-project-root') else '.'
skills = []
d = os.path.join(root, 'autonoma/skills')
if os.path.isdir(d):
    for f in os.listdir(d):
        if f.endswith('.md'):
            with open(os.path.join(d, f)) as fh:
                skills.append({'name': f, 'content': fh.read()})
print(json.dumps({'skills': skills}))
" | curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/artifacts" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @- || true
```

4. **If `AUTONOMA_REQUIRE_CONFIRMATION=true`:** Call `AskUserQuestion` with:
   - question: "Does this core flows table look correct? These flows determine how the test budget is distributed."
   - options: ["Yes, proceed to Step 3", "I want to suggest changes"]
   Wait for the user's response before proceeding.
   **Otherwise:** Skip the prompt and proceed directly to Step 3.

## Step 3: Generate Scenarios

Report step start:

```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
GENERATION_ID=$(cat "$AUTONOMA_ROOT/autonoma/.generation-id" 2>/dev/null || echo '')
echo "GENERATION_ID=${GENERATION_ID:-<empty>}"
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"step.started","data":{"step":2,"name":"Scenarios"}}' || true
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"log","data":{"message":"Mapping data model and designing test data environments..."}}' || true
```

Before spawning the subagent, fetch the SDK discover artifact and save it to `autonoma/discover.json`.
This step assumes Step 1 already produced:
- `AUTONOMA_SDK_ENDPOINT`
- `AUTONOMA_SHARED_SECRET`

Fetch and validate the artifact:

```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
mkdir -p "$AUTONOMA_ROOT/autonoma"
if [ -z "$AUTONOMA_SDK_ENDPOINT" ] || [ -z "$AUTONOMA_SHARED_SECRET" ]; then
  echo "ERROR: Step 1 did not leave AUTONOMA_SDK_ENDPOINT and AUTONOMA_SHARED_SECRET available."
  cleanup_dev_server
  exit 1
fi
BODY='{"action":"discover"}'
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$AUTONOMA_SHARED_SECRET" | sed 's/.*= //')
RESPONSE=$(curl -sS -w "\nHTTP_STATUS:%{http_code}" -X POST "$AUTONOMA_SDK_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "x-signature: $SIG" \
  -d "$BODY")
HTTP_STATUS=$(echo "$RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
DISCOVER_BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')
if [ "$HTTP_STATUS" != "200" ]; then
  echo "SDK discover failed (HTTP $HTTP_STATUS): $DISCOVER_BODY"
  cleanup_dev_server
  exit 1
fi
printf '%s\n' "$DISCOVER_BODY" > "$AUTONOMA_ROOT/autonoma/discover.json"
python3 "$(cat /tmp/autonoma-plugin-root)/hooks/validators/validate_discover.py" "$AUTONOMA_ROOT/autonoma/discover.json"
```

Spawn the `scenario-generator` subagent with the following task:

> Read the knowledge base from `autonoma/AUTONOMA.md`, `autonoma/skills/`, and the SDK discover
> artifact from `autonoma/discover.json`.
> Generate test data scenarios. Write the output to `autonoma/scenarios.md`.
> The file MUST have YAML frontmatter with scenario_count, scenarios summary, entity_types,
> discover metadata, and variable_fields. Prefer fixed, reviewable seed values by default. If a
> field needs uniqueness, prefer a planner-chosen hardcoded literal plus a discriminator before
> introducing a variable placeholder. Use variable fields only for truly dynamic values such as
> backend-generated or time-based fields. `generator` is optional and must not default to `faker`.
> Fetch the latest instructions from https://docs.agent.autonoma.app/llms/test-planner/step-2-scenarios.txt first.

**After the subagent completes:**
1. Verify `autonoma/discover.json` and `autonoma/scenarios.md` exist and are non-empty
2. Validate `autonoma/discover.json` using the plugin's validator
3. The PostToolUse hook will have validated the frontmatter format automatically
4. Read the file and present the summary to the user — scenario names, entity counts, entity types, discover schema counts, and the minimal variable field tokens that remain dynamic

Report step complete:

```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
GENERATION_ID=$(cat "$AUTONOMA_ROOT/autonoma/.generation-id" 2>/dev/null || echo '')
echo "GENERATION_ID=${GENERATION_ID:-<empty>}"
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"log","data":{"message":"Scenarios generated from SDK discover. Preserved standard/empty/large plus schema metadata, keeping variable fields minimal and intentional."}}' || true
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"step.completed","data":{"step":2,"name":"Scenarios"}}' || true
```

4. **If `AUTONOMA_REQUIRE_CONFIRMATION=true`:** Call `AskUserQuestion` with:
   - question: "Do these scenarios look correct? Most seed values should stay concrete, and only truly dynamic values should remain variable for later tests."
   - options: ["Yes, proceed to Step 4", "I want to suggest changes"]
   Wait for the user's response before proceeding.
   **Otherwise:** Skip the prompt and proceed directly to Step 4.

## Step 4: Generate E2E Test Cases

Report step start:

```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
GENERATION_ID=$(cat "$AUTONOMA_ROOT/autonoma/.generation-id" 2>/dev/null || echo '')
echo "GENERATION_ID=${GENERATION_ID:-<empty>}"
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"step.started","data":{"step":3,"name":"E2E Tests"}}' || true
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"log","data":{"message":"Generating E2E test cases from knowledge base and scenarios..."}}' || true
```

Spawn the `test-case-generator` subagent with the following task:

> Read the knowledge base from `autonoma/AUTONOMA.md`, skills from `autonoma/skills/`,
> and scenarios from `autonoma/scenarios.md`.
> Generate complete E2E test cases as markdown files in `autonoma/qa-tests/`.
> You MUST create `autonoma/qa-tests/INDEX.md` with frontmatter containing total_tests,
> total_folders, folder breakdown, and coverage_correlation.
> Each test file MUST have frontmatter with title, description, criticality, scenario, and flow.
> Treat `scenarios.md` as fixture input only. Do not generate tests whose purpose is to verify
> scenario counts, seeded inventories, or Environment Factory correctness. Only reference
> scenario data when it is needed to test a real user-facing app behavior.
> Fetch the latest instructions from https://docs.agent.autonoma.app/llms/test-planner/step-3-e2e-tests.txt first.

**After the subagent completes:**
1. Verify `autonoma/qa-tests/INDEX.md` exists and is non-empty
2. The PostToolUse hook will have validated the INDEX frontmatter and individual test file frontmatter
3. Read the INDEX.md and present the summary to the user — total tests, folder breakdown, coverage correlation

Report step complete and upload test cases:

```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
GENERATION_ID=$(cat "$AUTONOMA_ROOT/autonoma/.generation-id" 2>/dev/null || echo '')
echo "GENERATION_ID=${GENERATION_ID:-<empty>}"
TEST_COUNT=$(find "$AUTONOMA_ROOT/autonoma/qa-tests" -name '*.md' ! -name 'INDEX.md' 2>/dev/null | wc -l | tr -d ' ')
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"log\",\"data\":{\"message\":\"Generated ${TEST_COUNT} test cases. Uploading to dashboard...\"}}" || true
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"step.completed","data":{"step":3,"name":"E2E Tests"}}' || true
[ -n "$GENERATION_ID" ] && python3 -c "
import os, json
proj_root = open('/tmp/autonoma-project-root').read().strip() if os.path.exists('/tmp/autonoma-project-root') else '.'
qa_dir = os.path.join(proj_root, 'autonoma/qa-tests')
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
                entry['folder'] = folder
            test_cases.append(entry)
print(json.dumps({'testCases': test_cases}))
" | curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/artifacts" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @- || true
```

4. **If `AUTONOMA_REQUIRE_CONFIRMATION=true`:** Call `AskUserQuestion` with:
   - question: "Does this test distribution look correct? The total test count should roughly correlate with the number of routes and features in your app."
   - options: ["Yes, proceed to Step 5", "I want to suggest changes"]
   Wait for the user's response before proceeding.
   **Otherwise:** Skip the prompt and proceed directly to Step 5.

## Step 5: Scenario Validation

Report step start:

```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
GENERATION_ID=$(cat "$AUTONOMA_ROOT/autonoma/.generation-id" 2>/dev/null || echo '')
echo "GENERATION_ID=${GENERATION_ID:-<empty>}"
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"step.started","data":{"step":4,"name":"Scenario Validation"}}' || true
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"log","data":{"message":"Validating planned scenarios against the live SDK endpoint..."}}' || true
```

Spawn the `scenario-validator` subagent with the following task:

> Read `autonoma/discover.json` and `autonoma/scenarios.md`.
> Validate the planned scenarios against the existing live SDK endpoint without editing backend code.
> Smoke-test the signed `discover -> up -> down` lifecycle, validate `standard`, `empty`, and `large`,
> write approved recipes to `autonoma/scenario-recipes.json`, and run:
> `python3 "$(cat /tmp/autonoma-plugin-root)/hooks/preflight_scenario_recipes.py" autonoma/scenario-recipes.json`
> Do NOT install packages, edit backend code, modify SDK source, modify DB schemas or migrations, or create branches/commits/PRs.

**After the subagent completes:**
1. Verify `autonoma/scenario-recipes.json` exists and is non-empty
2. Run the preflight helper if the subagent did not already do so
3. If preflight fails, stop and report the failure without attempting code changes
4. Present the results to the user — endpoint validated, smoke-test results, per-scenario validation results, any remaining deployment issues

Run and enforce preflight:

```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
python3 "$(cat /tmp/autonoma-plugin-root)/hooks/preflight_scenario_recipes.py" "$AUTONOMA_ROOT/autonoma/scenario-recipes.json"
if [ $? -ne 0 ]; then
  echo "ERROR: Scenario recipe preflight failed."
  cleanup_dev_server
  exit 1
fi
```

Report step complete and upload scenario recipes:

```bash
AUTONOMA_ROOT=$(cat /tmp/autonoma-project-root 2>/dev/null || echo '.')
GENERATION_ID=$(cat "$AUTONOMA_ROOT/autonoma/.generation-id" 2>/dev/null || echo '')
echo "GENERATION_ID=${GENERATION_ID:-<empty>}"
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"log","data":{"message":"Uploading validated scenario recipes to setup..."}}' || true
if [ -n "$GENERATION_ID" ]; then
  RECIPE_PATH="$AUTONOMA_ROOT/autonoma/scenario-recipes.json"
  if ! python3 -c "import json; json.load(open('$RECIPE_PATH'))" 2>/dev/null; then
    echo "ERROR: scenario-recipes.json is not valid JSON. Step 5 cannot complete."
    cleanup_dev_server
    exit 1
  fi
  UPLOAD_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/scenario-recipe-versions" \
    -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
    -H "Content-Type: application/json" \
    -d @"$RECIPE_PATH")
  UPLOAD_STATUS=$(echo "$UPLOAD_RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
  UPLOAD_BODY=$(echo "$UPLOAD_RESPONSE" | sed '/HTTP_STATUS:/d')
  echo "Scenario recipe upload response (HTTP $UPLOAD_STATUS): $UPLOAD_BODY"
  if [ "$UPLOAD_STATUS" != "200" ] && [ "$UPLOAD_STATUS" != "201" ]; then
    echo "ERROR: Recipe upload failed (HTTP $UPLOAD_STATUS). Step 5 cannot complete."
    cleanup_dev_server
    exit 1
  fi

  VERIFY_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X GET "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/scenarios" \
    -H "Authorization: Bearer ${AUTONOMA_API_KEY}")
  VERIFY_STATUS=$(echo "$VERIFY_RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
  VERIFY_BODY=$(echo "$VERIFY_RESPONSE" | sed '/HTTP_STATUS:/d')
  if [ "$VERIFY_STATUS" != "200" ]; then
    echo "ERROR: Failed to verify uploaded scenarios (HTTP $VERIFY_STATUS)."
    cleanup_dev_server
    exit 1
  fi
fi
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"log","data":{"message":"Scenario validation completed."}}' || true
[ -n "$GENERATION_ID" ] && curl -f -X POST "${AUTONOMA_API_URL}/v1/setup/setups/${GENERATION_ID}/events" \
  -H "Authorization: Bearer ${AUTONOMA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"step.completed","data":{"step":4,"name":"Scenario Validation"}}' || true
cleanup_dev_server
```

## Completion

After all steps complete, summarize:
- **Step 1**: detected stack, installed packages, endpoint URL, PR URL if available
- **Step 2**: knowledge base location and core flow count
- **Step 3**: scenario count and entity types covered
- **Step 4**: total test count, folder breakdown, coverage correlation
- **Step 5**: scenario validation results, smoke-test status, and recipe upload status

If the pipeline aborts after Step 1 has started, run `cleanup_dev_server` before returning control to the user.
