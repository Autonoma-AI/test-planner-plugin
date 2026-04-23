#!/usr/bin/env python3
"""Validates autonoma/.scenario-validation.json."""
import json
import sys
from urllib.parse import urlparse


filepath = sys.argv[1]


def fail(message: str) -> None:
    print(message)
    sys.exit(1)


try:
    with open(filepath) as fh:
        payload = json.load(fh)
except Exception as exc:
    fail(f"Invalid JSON: {exc}")

if not isinstance(payload, dict):
    fail("Root must be a JSON object")

required = [
    "status",
    "preflightPassed",
    "smokeTestPassed",
    "validatedScenarios",
    "failedScenarios",
    "blockingIssues",
    "recipePath",
    "validationMode",
    "endpointUrl",
]
missing = [field for field in required if field not in payload]
if missing:
    fail(f"Missing required fields: {missing}")

if payload.get("status") not in {"ok", "failed"}:
    fail('status must be "ok" or "failed"')

for field in ["preflightPassed", "smokeTestPassed"]:
    if not isinstance(payload.get(field), bool):
        fail(f"{field} must be a boolean")

for field in ["validatedScenarios", "failedScenarios", "blockingIssues"]:
    value = payload.get(field)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        fail(f"{field} must be a list of strings")

recipe_path = payload.get("recipePath")
if not isinstance(recipe_path, str) or not recipe_path.strip():
    fail("recipePath must be a non-empty string")

validation_mode = payload.get("validationMode")
if validation_mode not in {"sdk-check", "endpoint-lifecycle"}:
    fail('validationMode must be "sdk-check" or "endpoint-lifecycle"')

endpoint_url = payload.get("endpointUrl")
if not isinstance(endpoint_url, str) or not endpoint_url.strip():
    fail("endpointUrl must be a non-empty string")
parsed = urlparse(endpoint_url)
if parsed.scheme not in {"http", "https"} or not parsed.netloc:
    fail("endpointUrl must be an absolute http/https URL")

# Login probe result — required when status == "ok" so .endpoint-validated is
# never written unless at least one scenario proved that the returned auth
# actually reaches a logged-in state in a real browser. Skipped results (e.g.
# agent-browser unavailable) are accepted but flagged so the SDK consumer can
# decide whether to gate on the probe or only on lifecycle success.
probe = payload.get("loginProbe")
if payload.get("status") == "ok":
    if not isinstance(probe, dict):
        fail("loginProbe must be an object when status is 'ok'")
    if "ok" not in probe or not isinstance(probe["ok"], bool):
        fail("loginProbe.ok must be a boolean")
    skipped = bool(probe.get("skipped"))
    if not probe["ok"] and not skipped:
        fail("loginProbe.ok is false — status cannot be 'ok' while login probe failed")
    if probe["ok"]:
        mode = probe.get("mode")
        if mode not in {"cookies", "token", "form"}:
            fail("loginProbe.mode must be one of 'cookies', 'token', 'form' when ok")
        scenario = probe.get("scenario")
        if not isinstance(scenario, str) or not scenario.strip():
            fail("loginProbe.scenario must be a non-empty string when ok")
elif probe is not None and not isinstance(probe, dict):
    fail("loginProbe, when present, must be an object")

print("OK")
