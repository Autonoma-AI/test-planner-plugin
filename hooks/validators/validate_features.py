#!/usr/bin/env python3
"""Validates autonoma/features.json schema."""
import sys
import json

filepath = sys.argv[1]

try:
    data = json.load(open(filepath))
except Exception as e:
    print(f'Invalid JSON: {e}')
    sys.exit(1)

if not isinstance(data, dict):
    print('Root must be a JSON object')
    sys.exit(1)

# Required top-level fields
required = ['features', 'total_features', 'total_routes', 'total_api_routes']
missing = [f for f in required if f not in data]
if missing:
    print(f'Missing required fields: {missing}')
    sys.exit(1)

# Validate features array
features = data.get('features')
if not isinstance(features, list) or len(features) == 0:
    print('features must be a non-empty array')
    sys.exit(1)

valid_types = {'page', 'api', 'flow', 'component', 'modal', 'settings'}

for i, f in enumerate(features):
    if not isinstance(f, dict):
        print(f'features[{i}] must be an object')
        sys.exit(1)
    for field in ['name', 'type', 'path', 'core']:
        if field not in f:
            print(f'features[{i}] missing required field: {field}')
            sys.exit(1)
    if not isinstance(f['name'], str) or len(f['name'].strip()) == 0:
        print(f'features[{i}].name must be a non-empty string')
        sys.exit(1)
    if f['type'] not in valid_types:
        print(f'features[{i}].type must be one of {valid_types}, got: {f["type"]}')
        sys.exit(1)
    if not isinstance(f['path'], str) or len(f['path'].strip()) == 0:
        print(f'features[{i}].path must be a non-empty string')
        sys.exit(1)
    if not isinstance(f['core'], bool):
        print(f'features[{i}].core must be a boolean')
        sys.exit(1)

# Validate counts
tf = data.get('total_features')
if not isinstance(tf, int) or tf < 1:
    print('total_features must be a positive integer')
    sys.exit(1)

if tf != len(features):
    print(f'total_features ({tf}) does not match features array length ({len(features)})')
    sys.exit(1)

for count_field in ['total_routes', 'total_api_routes']:
    val = data.get(count_field)
    if not isinstance(val, int) or val < 0:
        print(f'{count_field} must be a non-negative integer')
        sys.exit(1)

# Verify at least one core feature
core_count = sum(1 for f in features if f['core'])
if core_count == 0:
    print('At least one feature must have core: true')
    sys.exit(1)

print('OK')
