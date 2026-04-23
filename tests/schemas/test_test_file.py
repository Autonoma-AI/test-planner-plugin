from pydantic import ValidationError
import pytest

from schemas.test_file import TestFileDocument as _TestFileDocument


VALID = {
    "title": "Login works",
    "description": "Checks a login flow",
    "criticality": "critical",
    "scenario": "standard",
    "flow": "login",
}


def test_test_file_accepts_valid_payload():
    assert _TestFileDocument.model_validate(VALID).criticality == "critical"


def test_test_file_rejects_unknown_criticality():
    with pytest.raises(ValidationError, match="Input should be 'critical'"):
        _TestFileDocument.model_validate({**VALID, "criticality": "ultra"})
