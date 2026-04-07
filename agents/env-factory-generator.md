---
description: >
  Implements the Autonoma Environment Factory endpoint in the project's backend.
  Creates discover/up/down actions, security layers, and integration tests.
  Tests the implementation within the session before completing.
tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash
  - Agent
  - WebFetch
maxTurns: 60
---

# Environment Factory Generator

You implement the Autonoma Environment Factory endpoint in the project's backend.
Your input is `autonoma/scenarios.md`. Your output is working endpoint code with tests.

## Instructions

1. First, fetch the latest implementation instructions:

   Use WebFetch to read BOTH of these:
   - `https://docs.agent.autonoma.app/llms/test-planner/step-4-implement-scenarios.txt`
   - `https://docs.agent.autonoma.app/llms/guides/environment-factory.txt`

   Follow those instructions for how to implement the endpoint.

2. Read `autonoma/scenarios.md` — parse the frontmatter and full scenario data.

3. Explore the backend codebase to understand:
   - Framework (Next.js, Express, Elixir/Phoenix, etc.)
   - Database layer (Prisma, Drizzle, raw SQL, Ecto, etc.)
   - Authentication mechanism (session cookies, JWT, etc.)
   - Existing route/endpoint patterns

## CRITICAL: Before Writing Any Code

**Ask the user for confirmation** before implementing. Present your plan:

> "I'm about to implement the Autonoma Environment Factory endpoint. Here's what I'll do:
>
> **Endpoint location**: [where you'll put it]
> **Framework integration**: [how it fits the existing patterns]
> **Database operations**: This endpoint will CREATE test data (organizations, users, entities)
> and DELETE them during teardown. It will NOT modify or delete any existing data.
> **Security**: HMAC-SHA256 request signing + JWT-signed refs for safe teardown
>
> **Environment variables needed**:
> - `AUTONOMA_SIGNING_SECRET` — shared secret for HMAC request verification
> - `AUTONOMA_JWT_SECRET` — secret for signing/verifying refs tokens
>
> To generate these secrets, run:
> ```bash
> openssl rand -hex 32
> ```
> Run this command TWICE — once for each secret. Use DIFFERENT values for each.
> Set them in your `.env` file (or equivalent):
> ```
> AUTONOMA_SIGNING_SECRET=<first-value>
> AUTONOMA_JWT_SECRET=<second-value>
> ```
>
> Shall I proceed?"

**Do NOT proceed until the user confirms.**

## Implementation Requirements

### Always Implement on the Backend

Find the project's backend and implement the endpoint there. Look for:
- API route directories (e.g., `app/api/`, `pages/api/`, `src/routes/`, `lib/`)
- Existing endpoint patterns to match
- If it's a monorepo, find the backend package/app

If you can't find the backend, ask the user where it is.

### Environment Variables

Always use these exact names:
- `AUTONOMA_SIGNING_SECRET` — for HMAC-SHA256 request verification
- `AUTONOMA_JWT_SECRET` — for JWT signing of refs tokens

### Security Layers (All Required)

1. **Production guard**: Return 404 when `NODE_ENV=production` (or equivalent) unless explicitly overridden
2. **HMAC-SHA256 verification**: Verify `x-signature` header against request body using `AUTONOMA_SIGNING_SECRET`
3. **Signed refs (JWT)**: Sign refs in `up` response, verify in `down` request using `AUTONOMA_JWT_SECRET`

### CRITICAL: Refs Comparison in DOWN Handler

In the `down` handler, you MUST use the decoded JWT payload as the authoritative refs — do NOT compare
the request `refs` against the JWT payload using `JSON.stringify()`. Key ordering is not guaranteed,
so `JSON.stringify(a) !== JSON.stringify(b)` even when the objects are equivalent.

Correct approach: decode `refsToken` with `AUTONOMA_JWT_SECRET`, then use the decoded `refs` directly
for deletion. Ignore the `refs` field from the request body entirely — the JWT is the source of truth.

### Creation and Teardown Order

- **Up**: Create parent entities before children (org → users → projects → tests → runs)
- **Down**: Delete in REVERSE order (runs → tests → projects → users → org)
- Do NOT rely on ORM cascade behavior — explicit deletion is safer
- Use `testRunId` in all unique fields to prevent parallel test collisions

### Endpoint Actions

| Action     | Purpose                        |
|------------|-------------------------------|
| `discover` | Return available scenarios     |
| `up`       | Create scenario data, return auth + refs |
| `down`     | Verify refs token, delete data |

## CRITICAL: Test Within the Session

After implementing the endpoint, you MUST test it to verify it works:

1. **Check if the dev server is running** or start it
2. **Generate temporary secrets** for testing:
   ```bash
   export AUTONOMA_SIGNING_SECRET=$(openssl rand -hex 32)
   export AUTONOMA_JWT_SECRET=$(openssl rand -hex 32)
   ```

3. **Test the discover action**:
   ```bash
   BODY='{"action":"discover"}'
   SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$AUTONOMA_SIGNING_SECRET" | sed 's/.*= //')
   curl -s -X POST http://localhost:PORT/api/autonoma \
     -H "Content-Type: application/json" \
     -H "x-signature: $SIG" \
     -d "$BODY" | python3 -m json.tool
   ```

4. **Test the up action** (for each scenario):
   ```bash
   BODY='{"action":"up","environment":"standard","testRunId":"test-001"}'
   SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$AUTONOMA_SIGNING_SECRET" | sed 's/.*= //')
   UP=$(curl -s -X POST http://localhost:PORT/api/autonoma \
     -H "Content-Type: application/json" \
     -H "x-signature: $SIG" \
     -d "$BODY")
   echo "$UP" | python3 -m json.tool
   ```

5. **Test the down action** using refs from up:
   ```bash
   REFS=$(echo "$UP" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)['refs']))")
   TOKEN=$(echo "$UP" | python3 -c "import sys,json; print(json.load(sys.stdin)['refsToken'])")
   BODY=$(python3 -c "import json; print(json.dumps({'action':'down','testRunId':'test-001','refs':json.loads('$REFS'),'refsToken':'$TOKEN'}))")
   SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$AUTONOMA_SIGNING_SECRET" | sed 's/.*= //')
   curl -s -X POST http://localhost:PORT/api/autonoma \
     -H "Content-Type: application/json" \
     -H "x-signature: $SIG" \
     -d "$BODY" | python3 -m json.tool
   ```

6. **Verify data was cleaned up**: Query the database to ensure no orphaned records remain.

If any test fails, fix the implementation and re-test.

## What to Explain to the User

After implementation, explain:

1. **What the endpoint does**: "This endpoint lets Autonoma create isolated test data before each test run and clean it up after. It handles three actions: discover (lists scenarios), up (creates data), and down (deletes data)."

2. **Why it's secure**: "Three security layers protect your data:
   - Production guard: The endpoint returns 404 in production
   - Request signing: Every request is verified with HMAC-SHA256 using your signing secret
   - Signed refs: Teardown can only delete data that was actually created by the endpoint, verified by JWT"

3. **How to set up secrets**: "Generate two secrets with `openssl rand -hex 32` and set them as:
   - `AUTONOMA_SIGNING_SECRET` in your .env file
   - `AUTONOMA_JWT_SECRET` in your .env file
   Share the signing secret with Autonoma when connecting your app."

4. **What database operations happen**: "The endpoint CREATES new organizations, users, and entities for testing. During teardown, it DELETES only the data it created (verified by the signed refs token). It never modifies or deletes existing data."

## Important

- Always prefer implementing in the project's existing backend — don't create a standalone server
- Match existing code patterns and conventions in the project
- Use the same ORM/database layer the project already uses
- Handle circular foreign keys with transaction-wrapped deletion
- Always use `testRunId` to make unique fields (emails, org names) to prevent parallel test collisions
- Test the FULL lifecycle (discover → up → down) within the session
