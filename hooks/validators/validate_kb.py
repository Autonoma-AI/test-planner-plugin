#!/usr/bin/env python3
"""Validates AUTONOMA.md frontmatter format."""
import sys
import yaml

filepath = sys.argv[1]
content = open(filepath).read()

if not content.startswith('---'):
    print('File must start with YAML frontmatter (---)')
    sys.exit(1)

parts = content.split('---', 2)
if len(parts) < 3:
    print('Missing closing --- for frontmatter')
    sys.exit(1)

try:
    fm = yaml.safe_load(parts[1])
except Exception as e:
    print(f'Invalid YAML in frontmatter: {e}')
    sys.exit(1)

if not isinstance(fm, dict):
    print('Frontmatter must be a YAML mapping')
    sys.exit(1)

# Required fields
required = ['app_name', 'app_description', 'core_flows', 'feature_count', 'skill_count']
missing = [f for f in required if f not in fm]
if missing:
    print(f'Missing required frontmatter fields: {missing}')
    sys.exit(1)

# Validate app_description
desc = fm.get('app_description', '')
if not isinstance(desc, str) or len(desc.strip()) < 20:
    print('app_description must be a string with at least 2 sentences (20+ chars)')
    sys.exit(1)

# Validate core_flows
flows = fm.get('core_flows')
if not isinstance(flows, list) or len(flows) == 0:
    print('core_flows must be a non-empty list')
    sys.exit(1)

has_core = False
for i, flow in enumerate(flows):
    if not isinstance(flow, dict):
        print(f'core_flows[{i}] must be a mapping with feature, description, core')
        sys.exit(1)
    for field in ['feature', 'description', 'core']:
        if field not in flow:
            print(f'core_flows[{i}] missing required field: {field}')
            sys.exit(1)
    if not isinstance(flow['core'], bool):
        print(f'core_flows[{i}].core must be a boolean (true/false)')
        sys.exit(1)
    if flow['core']:
        has_core = True

if not has_core:
    print('At least one core_flow must have core: true')
    sys.exit(1)

# Validate counts
for count_field in ['feature_count', 'skill_count']:
    val = fm.get(count_field)
    if not isinstance(val, int) or val < 1:
        print(f'{count_field} must be a positive integer')
        sys.exit(1)

print('OK')
