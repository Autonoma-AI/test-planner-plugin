from pydantic import ValidationError
import pytest

from schemas.discover import DiscoverDocument


VALID = {
    "schema": {
        "models": [
            {
                "name": "Organization",
                "fields": [
                    {"name": "id", "type": "String", "isRequired": True, "isId": True, "hasDefault": True}
                ],
            }
        ],
        "edges": [],
        "relations": [],
        "scopeField": "organizationId",
    }
}


def test_discover_accepts_valid_payload():
    assert DiscoverDocument.model_validate(VALID).schema.models[0].name == "Organization"


def test_discover_rejects_unsupported_type_format():
    payload = {
        "schema": {
            **VALID["schema"],
            "models": [{"name": "Org", "fields": [{**VALID["schema"]["models"][0]["fields"][0], "type": "enum(foo"}]}],
        }
    }
    with pytest.raises(ValidationError, match="String should match pattern"):
        DiscoverDocument.model_validate(payload)
