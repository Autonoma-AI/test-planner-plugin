from pydantic import ValidationError
import pytest

from schemas.autonoma import AutonomaKB


VALID = {
    "app_name": "My App",
    "app_description": "A full-featured app for managing projects.",
    "feature_count": 1,
    "skill_count": 1,
    "core_flows": [{"feature": "login", "description": "User logs in", "core": True}],
}


def test_autonoma_accepts_valid_payload():
    assert AutonomaKB.model_validate(VALID).app_name == "My App"


def test_autonoma_requires_a_core_flow():
    payload = {**VALID, "core_flows": [{**VALID["core_flows"][0], "core": False}]}
    with pytest.raises(ValidationError, match="At least one core_flow"):
        AutonomaKB.model_validate(payload)
