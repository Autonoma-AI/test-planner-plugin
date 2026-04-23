from pydantic import ValidationError
import pytest

from schemas.entity_audit import EntityAuditDocument


VALID = {
    "model_count": 2,
    "factory_count": 1,
    "models": [
        {
            "name": "Organization",
            "independently_created": True,
            "creation_file": "factories/org.ts",
            "creation_function": "createOrg",
            "created_by": [],
        },
        {
            "name": "User",
            "independently_created": False,
            "created_by": [{"owner": "Organization", "via": "users", "why": "nested"}],
        },
    ],
}


def test_entity_audit_accepts_valid_v2_payload():
    audit = EntityAuditDocument.model_validate(VALID)
    assert audit.computed_factory_count == 1


def test_entity_audit_rejects_missing_owner():
    payload = {**VALID, "models": [VALID["models"][0], {**VALID["models"][1], "created_by": []}]}
    with pytest.raises(ValidationError, match="has no created_by entries"):
        EntityAuditDocument.model_validate(payload)
