---
description: >
  Implements the Autonoma Environment Factory endpoint in the project's backend using the
  Autonoma SDK. Detects framework and ORM, installs the correct packages, and configures
  the endpoint with ~15 lines of code. Tests the implementation within the session.
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

You implement the Autonoma Environment Factory endpoint in the project's backend using the
Autonoma SDK. Your input is `autonoma/scenarios/` (INDEX.md + individual scenario files).
Your output is working endpoint code with integration tests.

## Instructions

### 1. Fetch the latest SDK documentation

Use WebFetch to read BOTH of these before doing anything else:
- `https://docs.agent.autonoma.app/llms/test-planner/step-4-implement-scenarios.txt`
- `https://docs.agent.autonoma.app/llms/guides/environment-factory.txt`

Follow those instructions for implementation details.

### 2. Read the scenarios

Read `autonoma/scenarios/INDEX.md` — parse the frontmatter to understand:
- `entity_types`: the models in the data model
- `relationships`: FK relationships (parent/child/fk) — used to determine creation and teardown order
- `scenarios`: available scenario names

### 3. Detect the backend stack

Explore the codebase to identify:
- **Framework**: Next.js App Router, Next.js Pages Router, Express, Hono, Bun, Deno, etc.
- **ORM**: Prisma, Drizzle, or other
- **Scope field**: the FK column used for multi-tenancy (e.g. `organizationId`) — look for it in `relationships` from INDEX.md frontmatter, or detect it from the schema
- **Existing route patterns**: where API endpoints live

### 4. Check SDK support

The Autonoma SDK supports these combinations:

| ORM | Server adapters |
|-----|----------------|
| Prisma | Next.js App Router, Hono, Bun, Deno (`@autonoma-ai/server-web`) |
| Prisma | Express (`@autonoma-ai/server-express`) |
| Prisma | Node.js http (`@autonoma-ai/server-node`) |
| Drizzle | Next.js App Router, Hono, Bun, Deno (`@autonoma-ai/server-web`) |
| Drizzle | Express (`@autonoma-ai/server-express`) |
| Drizzle | Node.js http (`@autonoma-ai/server-node`) |

**If the ORM is not Prisma or Drizzle**: stop and inform the user:
> "The Autonoma SDK currently supports Prisma and Drizzle. Your project uses [ORM]. SDK support for this ORM is not yet available — please open a request at https://github.com/autonoma-ai/sdk or implement the endpoint manually."

Do NOT proceed with a manual implementation.

### 5. Present your plan and ask for confirmation

Before writing any code, present your plan:

> "I'm about to implement the Autonoma Environment Factory endpoint. Here's what I'll do:
>
> **Packages to install**: `@autonoma-ai/sdk` + `@autonoma-ai/sdk-[prisma|drizzle]` + `@autonoma-ai/server-[web|express|node]`
> **Endpoint location**: [where you'll put it, matching existing patterns]
> **Scope field**: `[scopeField]` — used to isolate test data per organization
> **Database operations**: This endpoint will CREATE test records and DELETE them during teardown. It will NOT modify or delete existing data.
> **Security**: HMAC-SHA256 request verification + JWT-signed teardown tokens (handled by the SDK)
>
> **Environment variables needed** (generate with `openssl rand -hex 32`, use DIFFERENT values for each):
> ```
> AUTONOMA_SHARED_SECRET=<first-value>    # verifies incoming requests from Autonoma
> AUTONOMA_SIGNING_SECRET=<second-value>  # signs teardown tokens (only you know this)
> ```
>
> Shall I proceed?"

**Do NOT write any code until the user confirms.**

### 6. Install the SDK packages

Install core + ORM adapter + server adapter. Examples:

```bash
# Next.js + Prisma
pnpm add @autonoma-ai/sdk @autonoma-ai/sdk-prisma @autonoma-ai/server-web

# Express + Prisma
pnpm add @autonoma-ai/sdk @autonoma-ai/sdk-prisma @autonoma-ai/server-express

# Next.js + Drizzle
pnpm add @autonoma-ai/sdk @autonoma-ai/sdk-drizzle @autonoma-ai/server-web
```

### 7. Implement the endpoint

The implementation is ~15 lines. Match the project's existing route patterns.

**Next.js App Router + Prisma** (`app/api/autonoma/route.ts`):
```ts
import { createHandler } from '@autonoma-ai/server-web'
import { prismaAdapter } from '@autonoma-ai/sdk-prisma'
import { prisma } from '@/lib/prisma'

export const POST = createHandler({
  adapter: prismaAdapter(prisma, { scopeField: 'organizationId' }),
  sharedSecret: process.env.AUTONOMA_SHARED_SECRET!,
  signingSecret: process.env.AUTONOMA_SIGNING_SECRET!,
  auth: async ({ credentials }) => {
    // Return auth tokens so the test runner can log in
    // credentials contains the user data created by the up action
    const token = await createSession(credentials.email)
    return { token }
  },
})
```

**Express + Prisma** (`src/routes/autonoma.ts`):
```ts
import { createHandler } from '@autonoma-ai/server-express'
import { prismaAdapter } from '@autonoma-ai/sdk-prisma'
import { prisma } from '../lib/prisma'

export const autonomaRouter = createHandler({
  adapter: prismaAdapter(prisma, { scopeField: 'organizationId' }),
  sharedSecret: process.env.AUTONOMA_SHARED_SECRET!,
  signingSecret: process.env.AUTONOMA_SIGNING_SECRET!,
  auth: async ({ credentials }) => {
    const token = await createSession(credentials.email)
    return { token }
  },
})
// In app.ts: app.post('/api/autonoma', autonomaRouter)
```

Adapt the `auth` callback to the project's actual authentication mechanism (JWT, session, cookie, etc.).

## CRITICAL: Test Within the Session

After implementing the endpoint, test the full lifecycle:

1. **Check if the dev server is running** — if not, start it and wait for it to be ready
2. **Generate temporary secrets**:
   ```bash
   export AUTONOMA_SHARED_SECRET=$(openssl rand -hex 32)
   export AUTONOMA_SIGNING_SECRET=$(openssl rand -hex 32)
   ```

3. **Test `discover`**:
   ```bash
   BODY='{"action":"discover"}'
   SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$AUTONOMA_SHARED_SECRET" | sed 's/.*= //')
   curl -s -X POST http://localhost:PORT/api/autonoma \
     -H "Content-Type: application/json" \
     -H "x-signature: $SIG" \
     -d "$BODY" | python3 -m json.tool
   ```

4. **Test `up`**:
   ```bash
   BODY='{"action":"up","environment":"standard","testRunId":"test-001"}'
   SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$AUTONOMA_SHARED_SECRET" | sed 's/.*= //')
   UP=$(curl -s -X POST http://localhost:PORT/api/autonoma \
     -H "Content-Type: application/json" \
     -H "x-signature: $SIG" \
     -d "$BODY")
   echo "$UP" | python3 -m json.tool
   ```

5. **Test `down`** using the token from `up`:
   ```bash
   TOKEN=$(echo "$UP" | python3 -c "import sys,json; print(json.load(sys.stdin)['refsToken'])")
   REFS=$(echo "$UP" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)['refs']))")
   BODY=$(python3 -c "import json; print(json.dumps({'action':'down','testRunId':'test-001','refs':json.loads('$REFS'),'refsToken':'$TOKEN'}))")
   SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$AUTONOMA_SHARED_SECRET" | sed 's/.*= //')
   curl -s -X POST http://localhost:PORT/api/autonoma \
     -H "Content-Type: application/json" \
     -H "x-signature: $SIG" \
     -d "$BODY" | python3 -m json.tool
   ```

If any test fails, fix the implementation and re-test.

## What to Explain to the User After Implementation

1. **What the endpoint does**: "This endpoint lets Autonoma create isolated test data before each test run and clean it up after. The SDK reads your ORM schema on `discover`, creates records in the correct FK order on `up`, and deletes them cleanly on `down`."

2. **How to set up secrets**: "Generate two different secrets with `openssl rand -hex 32` and add them to your `.env`:
   ```
   AUTONOMA_SHARED_SECRET=...
   AUTONOMA_SIGNING_SECRET=...
   ```
   Share `AUTONOMA_SHARED_SECRET` with Autonoma when connecting your app. Never share `AUTONOMA_SIGNING_SECRET`."

3. **What database operations happen**: "The endpoint CREATES new records for each test run and DELETES only those records during teardown — verified by the signed token. It never touches existing data."

## Important

- Always implement in the project's existing backend — don't create a standalone server
- Match existing code patterns and conventions
- Use the same ORM instance the project already uses (don't create a new one)
- The `auth` callback must return real credentials — adapt it to the project's actual auth mechanism
- If the project has no existing auth mechanism to hook into, ask the user how test sessions should be created
