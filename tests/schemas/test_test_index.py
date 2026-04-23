from pydantic import ValidationError
import pytest

from schemas.features import FeaturesDocument
from schemas.test_index import TestIndexDocument as _TestIndexDocument, cross_check


VALID = {
    "total_tests": 2,
    "total_folders": 1,
    "folders": [
        {
            "name": "auth",
            "description": "Auth",
            "test_count": 2,
            "critical": 1,
            "high": 1,
            "mid": 0,
            "low": 0,
        }
    ],
    "coverage_correlation": {
        "routes_or_features": 1,
        "expected_test_range_min": 1,
        "expected_test_range_max": 10,
    },
}

FEATURES = {
    "total_features": 1,
    "total_routes": 1,
    "total_api_routes": 0,
    "features": [{"name": "Login", "type": "page", "path": "/login", "core": True}],
}


def test_test_index_accepts_valid_payload_and_features_cross_check():
    index = _TestIndexDocument.model_validate(VALID)
    features = FeaturesDocument.model_validate(FEATURES)
    cross_check(index, features)


def test_test_index_rejects_criticality_sum_mismatch():
    payload = {**VALID, "folders": [{**VALID["folders"][0], "high": 0}]}
    with pytest.raises(ValidationError, match="do not sum to test_count"):
        _TestIndexDocument.model_validate(payload)
