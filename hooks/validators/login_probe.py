#!/usr/bin/env python3
"""Login probe — spawns `claude -p` with the agent-browser skill to verify
that the `auth` payload returned by `up` actually reaches an authenticated
page in a real browser.

This script does NOT drive agent-browser itself. It hands the full task to
a `claude -p` subprocess so the agent can reason about the login UI, pick
selectors via `snapshot`, and adapt to non-standard forms. Context-isolated
from the main pipeline, same pattern as validate_factory_fidelity.py.

Input: JSON on stdin (or --input file).
Output: JSON on stdout (or --output file).

Exit codes:
  0  success OR skipped
  2  probe failure (login didn't work)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


TIMEOUT = int(os.environ.get("AUTONOMA_LOGIN_PROBE_TIMEOUT", "180"))
PLUGIN_ROOT_FILE = "/tmp/autonoma-plugin-root"


def _install_agent_browser() -> tuple[bool, str]:
    """Auto-install agent-browser. Returns (success, log)."""
    log: list[str] = []

    def _try(cmd: list[str], timeout: int = 600) -> bool:
        log.append(f"$ {' '.join(cmd)}")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except FileNotFoundError:
            log.append("  (command not found)")
            return False
        except subprocess.TimeoutExpired:
            log.append(f"  (timeout after {timeout}s)")
            return False
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-5:]
        log.extend(f"  {l}" for l in tail)
        return proc.returncode == 0

    installed = False
    if shutil.which("npm") and _try(["npm", "install", "-g", "agent-browser"]):
        installed = True
    elif shutil.which("brew") and _try(["brew", "install", "agent-browser"]):
        installed = True
    elif shutil.which("cargo") and _try(["cargo", "install", "agent-browser"]):
        installed = True

    if not installed:
        return False, "\n".join(log) or "no installer available (need npm, brew, or cargo)"

    _try(["agent-browser", "install"], timeout=900)
    return shutil.which("agent-browser") is not None, "\n".join(log)


def _load_skill() -> str:
    """Load the agent-browser skill so claude -p knows the CLI surface."""
    # Try plugin root first, fall back to relative path.
    candidates = []
    if os.path.isfile(PLUGIN_ROOT_FILE):
        root = Path(open(PLUGIN_ROOT_FILE).read().strip())
        candidates.append(root / "skills" / "agent-browser" / "SKILL.md")
    candidates.append(Path(__file__).resolve().parent.parent.parent / "skills" / "agent-browser" / "SKILL.md")
    for p in candidates:
        if p.is_file():
            return p.read_text()
    return ""


def _build_prompt(cfg: dict, skill_text: str) -> str:
    auth_json = json.dumps(cfg.get("auth", {}), indent=2)
    base_url = cfg["baseUrl"]
    login_path = cfg.get("loginPath", "/login")
    protected_path = cfg.get("protectedPath", "/dashboard")
    marker_text = cfg.get("markerText", "")
    label = cfg.get("label", "probe")
    screenshot_dir = cfg.get("screenshotDir", "autonoma/.login-probe")

    return f"""You are a login probe. You have access to `agent-browser`, a headless browser
CLI. Use it via Bash to verify that the auth credentials below actually reach
an authenticated page.

## agent-browser reference

{skill_text}

## Task

The Environment Factory's `up` action returned the auth payload below.
Your job: use agent-browser to prove these credentials reach an authenticated
state on the running dev server. Always run headless (never --headed).
Always use `--session login-probe-{label}`.

**Base URL**: {base_url}
**Login path**: {login_path}
**Protected path**: {protected_path}
**Marker text** (substring expected on the authed page): {marker_text or "(none)"}
**Screenshot dir**: {screenshot_dir}

**Auth payload**:
```json
{auth_json}
```

## Strategy

1. If `auth` has `cookies`: navigate to {base_url}{login_path} first (to set
   the origin), then use `agent-browser cookies set <name> <value>` for each
   cookie. Then navigate to {base_url}{protected_path}. Check that the final
   URL is NOT {login_path} and optionally that the marker text appears.

2. If `auth` has `headers` or `token`: use
   `agent-browser open {base_url}{protected_path} --headers '<json>'` with
   the appropriate Authorization header. Check the final URL.

3. If `auth` has `user` (username/password): navigate to {base_url}{login_path},
   use `agent-browser snapshot -i` to find the form fields, fill them with
   `agent-browser fill <selector> <value>`, submit, then navigate to the
   protected path and check.

Try cookies first, then token/headers, then form. Stop at the first success.

## Output

When done, print EXACTLY one JSON object to stdout (no markdown fences, no
extra text before or after) with this shape:

Success:
{{"ok": true, "mode": "cookies|token|form", "evidence": {{"final_url": "...", "screenshot": "..."}}, "scenario": "{label}"}}

Failure:
{{"ok": false, "mode": "cookies|token|form", "failure": {{"category": "redirected_to_login|cookie_not_sent|marker_missing|bad_credentials|open_failed|fill_failed|submit_failed|unknown_ui", "detail": "one sentence explanation", "screenshot_path": "..."}}, "evidence": {{}}}}

Categories:
- redirected_to_login: cookie/token reached server but was rejected
- cookie_not_sent: browser didn't attach the cookie (path/domain/scope issue)
- marker_missing: page loaded but expected marker text absent
- bad_credentials: form submit with given user/pass didn't authenticate
- open_failed: couldn't navigate (server down, bad URL)
- fill_failed / submit_failed: form selectors didn't match
- unknown_ui: can't figure out the login UI

Take a screenshot before reporting: `agent-browser screenshot {screenshot_dir}/{label}.png`

Close the session when done: `agent-browser --session login-probe-{label} close`
"""


def _parse_verdict(text: str) -> dict:
    """Extract the JSON verdict from claude -p output.

    `claude -p --output-format json` wraps the assistant's text in an
    envelope like `{"result": "...", "duration_ms": ..., ...}`. We unwrap
    that first, then hunt for a JSON object with an "ok" key inside the
    assistant's response text.
    """
    text = text.strip()

    # Step 1: unwrap the claude envelope if present.
    inner = text
    try:
        envelope = json.loads(text)
        if isinstance(envelope, dict):
            raw = envelope.get("result") or envelope.get("text") or envelope.get("output") or ""
            if isinstance(raw, str) and raw.strip():
                inner = raw.strip()
            elif isinstance(raw, list):
                inner = "\n".join(str(x) for x in raw).strip()
            # If envelope itself has "ok", it IS the verdict (e.g. tests).
            if "ok" in envelope:
                return envelope
    except json.JSONDecodeError:
        pass

    # Step 2: try parsing the inner text as JSON directly.
    try:
        obj = json.loads(inner)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Step 3: strip markdown fences.
    cleaned = re.sub(r"^```[a-zA-Z]*\n", "", inner)
    cleaned = re.sub(r"\n```\s*$", "", cleaned)
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Step 4: find the last JSON object containing "ok" (the agent may
    # print narrative before the verdict).
    candidates = list(re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", inner))
    for m in reversed(candidates):
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict) and "ok" in obj:
                return obj
        except json.JSONDecodeError:
            continue

    return {"ok": False, "failure": {"category": "parse_error",
            "detail": f"Could not parse verdict from claude output: {inner[:300]}"}}


def run(cfg: dict) -> dict:
    # Ensure agent-browser is available.
    if shutil.which("agent-browser") is None:
        if os.environ.get("AUTONOMA_LOGIN_PROBE_NO_INSTALL") == "1":
            return {"ok": False, "skipped": True,
                    "reason": "agent-browser not on PATH; auto-install disabled via env."}
        ok, install_log = _install_agent_browser()
        if not ok:
            return {"ok": False, "skipped": True,
                    "reason": f"agent-browser auto-install failed.\n{install_log}"}

    # Ensure claude CLI is available.
    if shutil.which("claude") is None:
        return {"ok": False, "skipped": True,
                "reason": "claude CLI not on PATH."}

    # Check auth has anything to probe.
    auth = cfg.get("auth") or {}
    if not any(auth.get(k) for k in ("cookies", "headers", "token", "user")):
        return {"ok": False, "skipped": True,
                "reason": "auth payload has no cookies, headers, token, or user."}

    skill_text = _load_skill()
    prompt = _build_prompt(cfg, skill_text)

    cmd = [
        "claude", "-p", "--output-format", "json",
        "--allowedTools", "Bash(agent-browser *)",
        "--allowedTools", "Bash(mkdir *)",
    ]
    model = os.environ.get("AUTONOMA_LOGIN_PROBE_MODEL", "sonnet")
    if model:
        cmd.extend(["--model", model])

    try:
        proc = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "failure": {"category": "open_failed",
                "detail": f"claude -p timed out after {TIMEOUT}s"}}
    except FileNotFoundError:
        return {"ok": False, "skipped": True,
                "reason": "claude CLI not found."}

    if proc.returncode != 0:
        return {"ok": False, "failure": {"category": "open_failed",
                "detail": f"claude -p exited {proc.returncode}: {proc.stderr[:400]}"}}

    return _parse_verdict(proc.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input")
    parser.add_argument("--output")
    args = parser.parse_args()

    raw = Path(args.input).read_text() if args.input else sys.stdin.read()
    cfg = json.loads(raw)

    result = run(cfg)

    payload = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(payload)
    else:
        sys.stdout.write(payload + "\n")
    return 0 if result.get("ok") or result.get("skipped") else 2


if __name__ == "__main__":
    sys.exit(main())
