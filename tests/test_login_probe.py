"""End-to-end tests for hooks/validators/login_probe.py against the login-app
fixture. Requires both `agent-browser` and `claude` CLIs on PATH."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "hooks" / "validators" / "login_probe.py"
FIXTURE = ROOT / "tests" / "fixtures" / "login-app" / "server.py"

needs_agent_browser = pytest.mark.skipif(
    shutil.which("agent-browser") is None,
    reason="agent-browser CLI not installed",
)
needs_claude = pytest.mark.skipif(
    shutil.which("claude") is None,
    reason="claude CLI not installed",
)


@pytest.fixture(scope="module")
def fixture_server():
    sys.path.insert(0, str(FIXTURE.parent))
    import server  # type: ignore

    srv, _thread = server.serve(port=0)
    port = srv.server_address[1]
    base = f"http://127.0.0.1:{port}"
    for _ in range(20):
        try:
            import urllib.request
            urllib.request.urlopen(base + "/login", timeout=1).read()
            break
        except Exception:
            time.sleep(0.05)
    yield base
    srv.shutdown()
    sys.path.remove(str(FIXTURE.parent))


def run_probe(cfg: dict, tmp_path: Path, timeout: int = 300) -> tuple[int, dict]:
    cfg.setdefault("screenshotDir", str(tmp_path))
    cfg.setdefault("markerText", "demo")
    payload = json.dumps(cfg)
    env = {**os.environ, "PYTHONUNBUFFERED": "1",
           "AUTONOMA_LOGIN_PROBE_MODEL": "haiku",
           "AUTONOMA_LOGIN_PROBE_TIMEOUT": "240"}
    proc = subprocess.run(
        [sys.executable, str(PROBE)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    verdict = json.loads(proc.stdout) if proc.stdout.strip() else {}
    return proc.returncode, verdict


@needs_agent_browser
@needs_claude
def test_cookie_success(fixture_server, tmp_path):
    rc, verdict = run_probe({
        "baseUrl": fixture_server,
        "loginPath": "/login",
        "protectedPath": "/dashboard",
        "label": "cookie-ok",
        "auth": {"cookies": [
            {"name": "session", "value": "valid-token",
             "domain": "127.0.0.1", "path": "/"},
        ]},
    }, tmp_path)
    assert rc == 0, verdict
    assert verdict["ok"] is True
    assert verdict["mode"] == "cookies"


@needs_agent_browser
@needs_claude
def test_cookie_wrong_value(fixture_server, tmp_path):
    rc, verdict = run_probe({
        "baseUrl": fixture_server,
        "loginPath": "/login",
        "protectedPath": "/dashboard",
        "label": "cookie-wrong",
        "auth": {"cookies": [
            {"name": "session", "value": "garbage",
             "domain": "127.0.0.1", "path": "/"},
        ]},
    }, tmp_path)
    assert rc == 2
    assert verdict["ok"] is False
    assert verdict.get("failure", {}).get("category") in {
        "redirected_to_login", "cookie_not_sent", "marker_missing",
    }


@needs_agent_browser
@needs_claude
def test_form_success(fixture_server, tmp_path):
    rc, verdict = run_probe({
        "baseUrl": fixture_server,
        "loginPath": "/login",
        "protectedPath": "/dashboard",
        "label": "form-ok",
        "auth": {"user": {"username": "demo", "password": "demo123"}},
    }, tmp_path)
    assert rc == 0, verdict
    assert verdict["ok"] is True
    assert verdict["mode"] == "form"


@needs_agent_browser
@needs_claude
def test_form_bad_credentials(fixture_server, tmp_path):
    rc, verdict = run_probe({
        "baseUrl": fixture_server,
        "loginPath": "/login",
        "protectedPath": "/dashboard",
        "label": "form-bad",
        "auth": {"user": {"username": "demo", "password": "WRONG"}},
    }, tmp_path)
    assert rc == 2
    assert verdict["ok"] is False
    assert verdict.get("failure", {}).get("category") in {
        "bad_credentials", "redirected_to_login", "marker_missing",
    }


def test_agent_browser_missing_is_skip(tmp_path):
    """If agent-browser is not on PATH, probe exits 0 with skipped=True."""
    python_bin_dir = str(Path(sys.executable).parent)
    filtered = [p for p in os.environ.get("PATH", "").split(os.pathsep)
                if not (Path(p) / "agent-browser").exists()]
    path = os.pathsep.join([python_bin_dir, *filtered])
    assert shutil.which("agent-browser", path=path) is None, (
        "could not construct a PATH without agent-browser"
    )
    proc = subprocess.run(
        [sys.executable, str(PROBE)],
        input=json.dumps({
            "baseUrl": "http://127.0.0.1:1",
            "loginPath": "/login",
            "protectedPath": "/dashboard",
            "auth": {"cookies": [{"name": "x", "value": "y"}]},
        }),
        capture_output=True, text=True,
        env={"PATH": path, "PYTHONUNBUFFERED": "1",
             "AUTONOMA_LOGIN_PROBE_NO_INSTALL": "1"},
        timeout=15,
    )
    assert proc.returncode == 0, proc.stderr
    verdict = json.loads(proc.stdout)
    assert verdict.get("skipped") is True


def test_empty_auth_is_skip(tmp_path):
    """Auth payload with no credentials should skip."""
    rc, verdict = run_probe({
        "baseUrl": "http://127.0.0.1:1",
        "loginPath": "/login",
        "protectedPath": "/dashboard",
        "auth": {},
    }, tmp_path, timeout=15)
    assert rc == 0
    assert verdict.get("skipped") is True
