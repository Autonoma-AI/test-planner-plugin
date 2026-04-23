---
name: validate-auth-login
description: >
  Drive a real headless Chrome session through vercel-labs/agent-browser to
  verify that the `auth` payload returned by the Environment Factory's `up`
  action actually reaches an authenticated page. Invoked by the scenario-
  validator (Step 5) once per run, between `up` and `down`.
---

# Validate Auth / Login

Problem: Step 4 can produce a handler whose `up` response *looks* valid
(returns cookies / token / user) but the credentials don't actually log in —
cookie domain wrong, session secret mismatch, CSRF seed missing, token type
wrong, Set-Cookie attrs stripped. Downstream E2E tests then fail in an
opaque "redirected to /login" way.

Solution: before we write `.endpoint-validated`, drive a real browser with
the `auth` payload against the protected page and confirm the session
sticks. Headless. Deterministic (no LLM in the hot path).

## When to use

The scenario-validator agent invokes this skill once per run, on the first
scenario whose `up` response contains `auth.cookies`, `auth.headers`,
`auth.token`, or `auth.user`. Record the verdict in
`autonoma/.scenario-validation.json` under `loginProbe`.

If the probe fails, the scenario-validator's existing iterative-fix loop
picks up the failure category and fixes the handler (up to 5 iterations).

## How to run

```bash
python3 "$(cat /tmp/autonoma-plugin-root)/hooks/validators/login_probe.py" \
  --input - <<'JSON'
{
  "baseUrl":       "http://localhost:3000",
  "loginPath":     "/login",
  "protectedPath": "/dashboard",
  "markerText":    "Dashboard",
  "screenshotDir": "autonoma/.login-probe",
  "label":         "standard",
  "auth": {
    "cookies":  [{"name": "session", "value": "...", "domain": "localhost", "path": "/"}],
    "headers":  {"Authorization": "Bearer ..."},
    "token":    "...",
    "user":     {"username": "demo", "password": "demo123"}
  }
}
JSON
```

Reads `baseUrl`/`loginPath`/`protectedPath` from `autonoma/AUTONOMA.md`'s
login flow. `markerText` is the substring the probe looks for on the
protected page to confirm a logged-in state (usually the username echo or
a "Dashboard" header). Optional — if absent, the probe accepts any
non-login URL as success.

## Output contract

Single JSON object on stdout:

```json
{ "ok": true,  "mode": "cookies|token|form", "evidence": { "final_url": "...", "screenshot": "..." } }
{ "ok": false, "mode": "...", "failure": { "category": "...", "detail": "...", "screenshot_path": "..." } }
{ "ok": false, "skipped": true, "reason": "..." }
```

Exit code: `0` on success or skip, `2` on failure. Screenshots are written
to `autonoma/.login-probe/<label>-<mode>.png` so you can eyeball the state
when diagnosing a failure.

## Installing agent-browser

The probe auto-installs `agent-browser` on first run if it is not on PATH,
trying `npm install -g agent-browser`, then `brew install agent-browser`,
then `cargo install agent-browser` (whichever toolchain is available). It
also runs `agent-browser install` to download headless Chrome. Only if all
three installers are missing does the probe fall back to a structured skip —
the user never has to intervene.

Manual install fallback:

```bash
# macOS
brew install agent-browser

# or any OS via npm
npm install -g agent-browser

# then download the headless Chrome it drives:
agent-browser install
```

Runs headless by default. Never pass `--headed` in CI / pipeline context.

## Failure categories

| `failure.category`    | What it means                                               | Typical fix                                        |
|-----------------------|-------------------------------------------------------------|----------------------------------------------------|
| `redirected_to_login` | Cookie/token was sent but server rejected it.                | Check auth callback's session secret / token type. |
| `cookie_not_sent`     | Browser refused to attach the cookie.                        | Fix `domain`/`path`/`Secure`/`SameSite`/`HttpOnly`.|
| `marker_missing`      | Reached a non-login URL but expected post-login marker absent. | Update marker in KB, or fix handler render.        |
| `bad_credentials`     | Form submit with `auth.user` didn't authenticate.            | Align returned credentials with DB state.          |
| `open_failed`         | agent-browser couldn't navigate (server down, bad URL).      | Confirm dev server up, baseUrl reachable.          |
| `fill_failed` / `submit_failed` | Selectors don't match the login form.              | Supply correct `usernameSelector` / `passwordSelector` / `submitSelector`. |

## Tests

Fixture app + pytest coverage at `tests/fixtures/login-app/server.py` and
`tests/test_login_probe.py`. The fixture is a stdlib-only HTTP server with
hardcoded `demo`/`demo123` credentials, providing deterministic success and
failure paths for every category above.
