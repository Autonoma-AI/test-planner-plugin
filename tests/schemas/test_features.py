from pydantic import ValidationError
import pytest

from schemas.features import FeaturesDocument


VALID = {
    "total_features": 1,
    "total_routes": 2,
    "total_api_routes": 1,
    "features": [{"name": "Login", "type": "page", "path": "/login", "core": True}],
}


def test_features_accepts_valid_payload():
    assert FeaturesDocument.model_validate(VALID).features[0].name == "Login"


def test_features_rejects_count_mismatch():
    with pytest.raises(ValidationError, match="does not match features array length"):
        FeaturesDocument.model_validate({**VALID, "total_features": 2})
