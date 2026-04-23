from pydantic import ValidationError
import pytest

from schemas.scenarios import ScenariosDocument


VALID = {
    "scenario_count": 3,
    "scenarios": [
        {"name": "standard", "description": "Typical", "entity_types": ["user"], "total_entities": 1},
        {"name": "empty", "description": "Empty", "entity_types": ["user"], "total_entities": 0},
        {"name": "large", "description": "Large", "entity_types": ["user"], "total_entities": 100},
    ],
    "entity_types": [{"name": "user"}],
    "variable_fields": [],
    "planning_sections": ["schema_summary", "relationship_map", "variable_data_strategy"],
}


def test_scenarios_accepts_valid_payload():
    assert ScenariosDocument.model_validate(VALID).scenario_count == 3


def test_scenarios_rejects_unknown_variable_scenario():
    payload = {
        **VALID,
        "variable_fields": [
            {
                "token": "{{title}}",
                "entity": "Task",
                "scenarios": ["missing"],
                "reason": "varies",
                "test_reference": "task title",
            }
        ],
    }
    with pytest.raises(ValidationError, match="references unknown scenario"):
        ScenariosDocument.model_validate(payload)
