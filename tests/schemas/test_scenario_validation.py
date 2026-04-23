from pydantic import ValidationError
import pytest

from schemas.scenario_validation import ScenarioValidationDocument


VALID = {
    "status": "ok",
    "preflightPassed": True,
    "smokeTestPassed": True,
    "validatedScenarios": ["standard"],
    "failedScenarios": [],
    "blockingIssues": [],
    "recipePath": "autonoma/scenario-recipes.json",
    "validationMode": "sdk-check",
    "endpointUrl": "http://localhost:3000/api/autonoma",
}


def test_scenario_validation_accepts_valid_payload():
    assert ScenarioValidationDocument.model_validate(VALID).status == "ok"


def test_scenario_validation_rejects_relative_endpoint():
    with pytest.raises(ValidationError, match="absolute http/https URL"):
        ScenarioValidationDocument.model_validate({**VALID, "endpointUrl": "/api/autonoma"})
