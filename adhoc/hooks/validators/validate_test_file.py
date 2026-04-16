#!/usr/bin/env python3
"""Validates individual test file frontmatter format."""
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

required = ['title', 'description', 'criticality', 'scenario', 'flow']
missing = [f for f in required if f not in fm]
if missing:
    print(f'Missing required frontmatter fields: {missing}')
    sys.exit(1)

valid_criticality = {'critical', 'high', 'mid', 'low'}
crit = fm.get('criticality')
if crit not in valid_criticality:
    print(f'criticality must be one of {valid_criticality}, got: {crit}')
    sys.exit(1)

for field in ['title', 'description', 'scenario', 'flow']:
    val = fm.get(field)
    if not isinstance(val, str) or len(val.strip()) == 0:
        print(f'{field} must be a non-empty string')
        sys.exit(1)

print('OK')
