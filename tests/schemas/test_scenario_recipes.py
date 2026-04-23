from pydantic import ValidationError
import pytest

from schemas.discover import DiscoverDocument
from schemas.scenario_recipes import ScenarioRecipesDocument, cross_check


DISCOVER = {
    "schema": {
        "models": [
            {
                "name": "Organization",
                "fields": [
                    {"name": "name", "type": "String", "isRequired": True, "isId": False, "hasDefault": False}
                ],
            }
        ],
        "edges": [],
        "relations": [],
        "scopeField": "organizationId",
    }
}

VALID = {
    "version": 1,
    "source": {"discoverPath": "autonoma/discover.json", "scenariosPath": "autonoma/scenarios.md"},
    "validationMode": "sdk-check",
    "recipes": [
        {
            "name": name,
            "description": name,
            "create": {"Organization": [{"name": name}]},
            "validation": {"status": "validated", "method": "checkScenario", "phase": "ok"},
        }
        for name in ("standard", "empty", "large")
    ],
}


def test_scenario_recipes_accepts_valid_payload_and_discover_cross_check():
    recipes = ScenarioRecipesDocument.model_validate(VALID)
    discover = DiscoverDocument.model_validate(DISCOVER)
    cross_check(recipes, discover)


def test_scenario_recipes_rejects_unused_variable():
    payload = {
        **VALID,
        "recipes": [
            {**VALID["recipes"][0], "variables": {"unused": {"strategy": "literal", "value": "x"}}},
            *VALID["recipes"][1:],
        ],
    }
    with pytest.raises(ValidationError, match="unused variable definitions"):
        ScenarioRecipesDocument.model_validate(payload)
