#!/usr/bin/env python3
"""Validates autonoma/scenarios/INDEX.md frontmatter format."""
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
required = ['scenario_count', 'scenarios', 'entity_types']
missing = [f for f in required if f not in fm]
if missing:
    print(f'Missing required frontmatter fields: {missing}')
    sys.exit(1)

# Validate scenario_count
sc = fm.get('scenario_count')
if not isinstance(sc, int) or sc < 1:
    print('scenario_count must be an integer >= 1')
    sys.exit(1)

# Validate scenarios list
scenarios = fm.get('scenarios')
if not isinstance(scenarios, list) or len(scenarios) != sc:
    print(f'scenarios list length ({len(scenarios) if isinstance(scenarios, list) else "N/A"}) must match scenario_count ({sc})')
    sys.exit(1)

for i, s in enumerate(scenarios):
    if not isinstance(s, dict):
        print(f'scenarios[{i}] must be a mapping')
        sys.exit(1)
    for field in ['name', 'file', 'description']:
        if field not in s:
            print(f'scenarios[{i}] missing required field: {field}')
            sys.exit(1)
        if not isinstance(s[field], str) or not s[field].strip():
            print(f'scenarios[{i}].{field} must be a non-empty string')
            sys.exit(1)

# Validate entity_types
et = fm.get('entity_types')
if not isinstance(et, list) or len(et) == 0:
    print('entity_types must be a non-empty list')
    sys.exit(1)

for i, e in enumerate(et):
    if not isinstance(e, dict) or 'name' not in e:
        print(f'entity_types[{i}] must be a mapping with at least a "name" field')
        sys.exit(1)
    if not isinstance(e['name'], str) or not e['name'].strip():
        print(f'entity_types[{i}].name must be a non-empty string')
        sys.exit(1)

# Validate relationships (optional)
rels = fm.get('relationships')
if rels is not None:
    if not isinstance(rels, list):
        print('relationships must be a list')
        sys.exit(1)
    for i, r in enumerate(rels):
        if not isinstance(r, dict):
            print(f'relationships[{i}] must be a mapping')
            sys.exit(1)
        for field in ['parent', 'child', 'fk']:
            if field not in r:
                print(f'relationships[{i}] missing required field: {field}')
                sys.exit(1)

print('OK')
