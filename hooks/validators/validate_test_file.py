#!/usr/bin/env python3
"""Validates individual test file frontmatter format."""
import sys
import os
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
required = ['title', 'description', 'criticality', 'scenario', 'flow']
missing = [f for f in required if f not in fm]
if missing:
    print(f'Missing required frontmatter fields: {missing}')
    sys.exit(1)

# Validate criticality
valid_criticality = {'critical', 'high', 'mid', 'low'}
crit = fm.get('criticality')
if crit not in valid_criticality:
    print(f'criticality must be one of {valid_criticality}, got: {crit}')
    sys.exit(1)

# Validate string fields are non-empty
for field in ['title', 'description', 'flow']:
    val = fm.get(field)
    if not isinstance(val, str) or len(val.strip()) == 0:
        print(f'{field} must be a non-empty string')
        sys.exit(1)

# Validate scenario is an object with name and description
scenario = fm.get('scenario')
if not isinstance(scenario, dict):
    print('scenario must be a mapping with "name" and "description" fields')
    sys.exit(1)

for field in ['name', 'description']:
    val = scenario.get(field)
    if not isinstance(val, str) or not val.strip():
        print(f'scenario.{field} must be a non-empty string')
        sys.exit(1)

scenario_name = scenario['name']

# Cross-check: scenario file must exist in autonoma/scenarios/
path = os.path.abspath(filepath)
autonoma_dir = None
path_parts = path.split(os.sep)
for i in range(len(path_parts) - 1, -1, -1):
    if path_parts[i] == 'autonoma':
        autonoma_dir = os.sep.join(path_parts[:i + 1])
        break

if autonoma_dir:
    scenario_file = os.path.join(autonoma_dir, 'scenarios', f'{scenario_name}.md')
    if not os.path.isfile(scenario_file):
        print(f'scenario "{scenario_name}" not found: expected file at autonoma/scenarios/{scenario_name}.md')
        sys.exit(1)

print('OK')
