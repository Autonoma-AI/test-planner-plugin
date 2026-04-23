"""Tests for validate_features.py — features.json validation."""
import json
from conftest import run_validator

SCRIPT = 'validate_features.py'

VALID_DATA = {
    'total_features': 2,
    'total_routes': 3,
    'total_api_routes': 1,
    'features': [
        {'name': 'Login', 'type': 'page', 'path': '/login', 'core': True},
        {'name': 'Dashboard', 'type': 'page', 'path': '/dashboard', 'core': False},
    ],
}


def _json(data):
    return json.dumps(data)


def test_valid_features():
    code, out = run_validator(SCRIPT, _json(VALID_DATA), 'features.json')
    assert code == 0
    assert out == 'OK'


def test_invalid_json():
    code, out = run_validator(SCRIPT, '{not json', 'features.json')
    assert code == 1
    assert 'Invalid JSON' in out


def test_root_not_object():
    code, out = run_validator(SCRIPT, '[]', 'features.json')
    assert code == 1
    assert 'Root must be a JSON object' in out


def test_missing_required_fields():
    code, out = run_validator(SCRIPT, _json({'features': []}), 'features.json')
    assert code == 1
    assert 'total_features: Field required' in out


def test_empty_features_array():
    data = {**VALID_DATA, 'features': [], 'total_features': 0}
    code, out = run_validator(SCRIPT, _json(data), 'features.json')
    assert code == 1
    # Either "non-empty array" or "positive integer" for total_features=0
    assert code == 1


def test_feature_missing_name():
    data = {**VALID_DATA, 'features': [
        {'type': 'page', 'path': '/x', 'core': True},
    ], 'total_features': 1}
    code, out = run_validator(SCRIPT, _json(data), 'features.json')
    assert code == 1
    assert 'features[0].name: Field required' in out


def test_invalid_feature_type():
    data = {**VALID_DATA, 'features': [
        {'name': 'X', 'type': 'widget', 'path': '/x', 'core': True},
    ], 'total_features': 1}
    code, out = run_validator(SCRIPT, _json(data), 'features.json')
    assert code == 1
    assert "Input should be 'page'" in out


def test_total_features_mismatch():
    data = {**VALID_DATA, 'total_features': 99}
    code, out = run_validator(SCRIPT, _json(data), 'features.json')
    assert code == 1
    assert 'does not match features array length' in out


def test_no_core_feature():
    data = {**VALID_DATA, 'features': [
        {'name': 'A', 'type': 'page', 'path': '/a', 'core': False},
        {'name': 'B', 'type': 'api', 'path': '/b', 'core': False},
    ]}
    code, out = run_validator(SCRIPT, _json(data), 'features.json')
    assert code == 1
    assert 'At least one feature must have core: true' in out


def test_negative_total_routes():
    data = {**VALID_DATA, 'total_routes': -1}
    code, out = run_validator(SCRIPT, _json(data), 'features.json')
    assert code == 1
    assert 'total_routes: Input should be greater than or equal to 0' in out


def test_core_not_boolean():
    data = {**VALID_DATA, 'features': [
        {'name': 'A', 'type': 'page', 'path': '/a', 'core': 'yes'},
    ], 'total_features': 1}
    code, out = run_validator(SCRIPT, _json(data), 'features.json')
    assert code == 1
    assert 'features[0].core: Input should be a valid boolean' in out


def test_empty_name():
    data = {**VALID_DATA, 'features': [
        {'name': '  ', 'type': 'page', 'path': '/a', 'core': True},
    ], 'total_features': 1}
    code, out = run_validator(SCRIPT, _json(data), 'features.json')
    assert code == 1
    assert 'features[0].name: String should have at least 1 character' in out
