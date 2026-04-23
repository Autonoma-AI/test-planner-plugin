"""Tests for validate_scenario_validation.py."""
import json

from conftest import run_validator


SCRIPT = "validate_scenario_validation.py"


def valid_payload(**overrides):
    payload = {
        "status": "ok",
        "preflightPassed": True,
        "smokeTestPassed": True,
        "validatedScenarios": ["standard", "empty", "large"],
        "failedScenarios": [],
        "blockingIssues": [],
        "recipePath": "autonoma/scenario-recipes.json",
        "validationMode": "sdk-check",
        "endpointUrl": "http://127.0.0.1:3000/api/autonoma",
        "loginProbe": {
            "ok": True,
            "mode": "cookies",
            "scenario": "standard",
            "evidence": {"final_url": "http://127.0.0.1:3000/dashboard"},
        },
    }
    payload.update(overrides)
    return payload


def test_accepts_valid_payload():
    code, out = run_validator(SCRIPT, json.dumps(valid_payload()), filename=".scenario-validation.json")
    assert code == 0
    assert out == "OK"


def test_accepts_failed_status_payload():
    payload = valid_payload(
        status="failed",
        preflightPassed=False,
        validatedScenarios=["standard"],
        failedScenarios=["empty", "large"],
        blockingIssues=["duplicate email"],
    )
    # Failed-status payloads don't require a successful probe.
    payload.pop("loginProbe")
    code, out = run_validator(SCRIPT, json.dumps(payload), filename=".scenario-validation.json")
    assert code == 0
    assert out == "OK"


def test_accepts_ok_payload_with_skipped_probe():
    code, out = run_validator(
        SCRIPT,
        json.dumps(
            valid_payload(
                loginProbe={
                    "ok": False,
                    "skipped": True,
                    "reason": "agent-browser not installed",
                }
            )
        ),
        filename=".scenario-validation.json",
    )
    assert code == 0
    assert out == "OK"


def test_rejects_ok_payload_missing_probe():
    payload = valid_payload()
    payload.pop("loginProbe")
    code, out = run_validator(SCRIPT, json.dumps(payload), filename=".scenario-validation.json")
    assert code == 1
    assert "loginProbe" in out


def test_rejects_ok_payload_with_failed_probe():
    code, out = run_validator(
        SCRIPT,
        json.dumps(
            valid_payload(
                loginProbe={
                    "ok": False,
                    "mode": "cookies",
                    "failure": {"category": "redirected_to_login", "detail": "..."},
                }
            )
        ),
        filename=".scenario-validation.json",
    )
    assert code == 1
    assert "login probe failed" in out


def test_rejects_ok_probe_without_scenario():
    code, out = run_validator(
        SCRIPT,
        json.dumps(
            valid_payload(loginProbe={"ok": True, "mode": "token"})
        ),
        filename=".scenario-validation.json",
    )
    assert code == 1
    assert "scenario" in out


def test_rejects_missing_required_field():
    payload = valid_payload()
    payload.pop("recipePath")
    code, out = run_validator(SCRIPT, json.dumps(payload), filename=".scenario-validation.json")
    assert code == 1
    assert "Missing required fields" in out


def test_rejects_invalid_endpoint_url():
    code, out = run_validator(
        SCRIPT,
        json.dumps(valid_payload(endpointUrl="relative/path")),
        filename=".scenario-validation.json",
    )
    assert code == 1
    assert "absolute http/https URL" in out
