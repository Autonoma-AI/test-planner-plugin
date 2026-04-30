#!/usr/bin/env python3
"""Validates individual test file frontmatter format and test quality rules."""
import re
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
for field in ['title', 'description', 'scenario', 'flow']:
    val = fm.get(field)
    if not isinstance(val, str) or len(val.strip()) == 0:
        print(f'{field} must be a non-empty string')
        sys.exit(1)

# --- Quality checks on the body ---

body = parts[2]

# Extract the Steps section
steps_match = re.search(r'## Steps\s*\n(.*?)(?=\n## |\Z)', body, re.DOTALL)
if not steps_match:
    print('OK')
    sys.exit(0)

steps_text = steps_match.group(1)
step_lines = [line.strip() for line in steps_text.strip().split('\n')
               if re.match(r'^\d+\.?\s+', line.strip())]

# Quality check 1: No OR logic in assertions
for line in step_lines:
    step_body = re.sub(r'^\d+\.?\s*', '', line)
    if re.match(r'(Assert|assert)', step_body):
        # Check for " or " as a word boundary (not inside quotes for field values)
        # Allow "or" inside quoted strings like "New York or bust" by checking
        # for unquoted occurrences
        unquoted = re.sub(r'"[^"]*"', '', step_body)
        unquoted = re.sub(r"'[^']*'", '', unquoted)
        if re.search(r'\bor\b', unquoted, re.IGNORECASE):
            print(f'QUALITY: Assertion contains OR logic. Assertions must be deterministic '
                  f'- describe exactly one condition, no alternatives.\n'
                  f'  Line: {line.strip()}')
            sys.exit(1)

# Quality check 2: At least one non-assert action in Steps
action_pattern = re.compile(
    r'^(click|type|scroll|hover|drag|read|refresh|clear|select|toggle|open|close|check|uncheck)',
    re.IGNORECASE
)
action_count = 0
for line in step_lines:
    step_body = re.sub(r'^\d+\.?\s*', '', line).strip()
    if action_pattern.match(step_body):
        action_count += 1

if action_count == 0:
    print('QUALITY: Test has no state-changing actions. Every test must perform at least '
          'one click, type, scroll, hover, drag, or other interaction that changes '
          'application state. A test with only assertions is not a test.')
    sys.exit(1)

print('OK')
