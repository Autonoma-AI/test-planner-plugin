#!/usr/bin/env python3
"""Validates qa-tests/INDEX.md frontmatter format."""
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
required = ['total_tests', 'total_folders', 'folders', 'coverage_correlation']
missing = [f for f in required if f not in fm]
if missing:
    print(f'Missing required frontmatter fields: {missing}')
    sys.exit(1)

# Validate total_tests
tt = fm.get('total_tests')
if not isinstance(tt, int) or tt < 1:
    print('total_tests must be a positive integer')
    sys.exit(1)

# Validate total_folders
tf = fm.get('total_folders')
if not isinstance(tf, int) or tf < 1:
    print('total_folders must be a positive integer')
    sys.exit(1)

# Validate folders
folders = fm.get('folders')
if not isinstance(folders, list) or len(folders) != tf:
    print(f'folders list length ({len(folders) if isinstance(folders, list) else "N/A"}) must match total_folders ({tf})')
    sys.exit(1)

computed_total = 0
for i, f in enumerate(folders):
    if not isinstance(f, dict):
        print(f'folders[{i}] must be a mapping')
        sys.exit(1)
    for field in ['name', 'description', 'test_count', 'critical', 'high', 'mid', 'low']:
        if field not in f:
            print(f'folders[{i}] missing required field: {field}')
            sys.exit(1)
    tc = f.get('test_count')
    if not isinstance(tc, int) or tc < 1:
        print(f'folders[{i}].test_count must be a positive integer')
        sys.exit(1)
    # Verify criticality counts sum to test_count
    crit_sum = 0
    for level in ['critical', 'high', 'mid', 'low']:
        val = f.get(level)
        if not isinstance(val, int) or val < 0:
            print(f'folders[{i}].{level} must be a non-negative integer')
            sys.exit(1)
        crit_sum += val
    if crit_sum != tc:
        print(f'folders[{i}]: criticality counts ({crit_sum}) do not sum to test_count ({tc})')
        sys.exit(1)
    computed_total += tc

if computed_total != tt:
    print(f'Sum of folder test_counts ({computed_total}) does not match total_tests ({tt})')
    sys.exit(1)

# Validate coverage_correlation
cc = fm.get('coverage_correlation')
if not isinstance(cc, dict):
    print('coverage_correlation must be a mapping')
    sys.exit(1)
for field in ['routes_or_features', 'expected_test_range_min', 'expected_test_range_max']:
    if field not in cc:
        print(f'coverage_correlation missing required field: {field}')
        sys.exit(1)

rf = cc.get('routes_or_features')
if not isinstance(rf, int) or rf < 1:
    print('coverage_correlation.routes_or_features must be a positive integer')
    sys.exit(1)

tmin = cc.get('expected_test_range_min')
tmax = cc.get('expected_test_range_max')
if not isinstance(tmin, int) or not isinstance(tmax, int):
    print('expected_test_range_min and expected_test_range_max must be integers')
    sys.exit(1)
if tmin > tmax:
    print('expected_test_range_min must be <= expected_test_range_max')
    sys.exit(1)
if tt < tmin:
    print(f'total_tests ({tt}) is below minimum ({tmin}) for {rf} routes/features. Too few tests — add more coverage.')
    sys.exit(1)

# --- Independent file count check ---
# Count route/page files in the codebase to sanity-check the agent's routes_or_features number.
# This catches cases where the agent underreports features to justify fewer tests.
import os, glob

index_dir = os.path.dirname(filepath)  # autonoma/qa-tests/
project_root = os.path.dirname(os.path.dirname(index_dir))  # project root

route_patterns = [
    '**/page.tsx', '**/page.jsx', '**/page.ts', '**/page.js',       # Next.js app router
    'pages/**/*.tsx', 'pages/**/*.jsx', 'pages/**/*.ts',             # Next.js pages router
    'src/pages/**/*.tsx', 'src/pages/**/*.jsx',                      # Vite/CRA
    'src/routes/**/*.tsx', 'src/routes/**/*.jsx',                    # Remix/React Router
    '**/+page.svelte',                                               # SvelteKit
    'src/views/**/*.vue',                                            # Vue
    'lib/*_web/controllers/**/*.ex',                                 # Phoenix
    'app/controllers/**/*.rb',                                       # Rails
]

found_files = set()
for pattern in route_patterns:
    found_files.update(glob.glob(os.path.join(project_root, pattern), recursive=True))

if found_files:
    file_count = len(found_files)
    min_tests_for_files = file_count * 2  # gross lower bound: at least 2 tests per route file
    if tt < min_tests_for_files:
        print(f'total_tests ({tt}) looks too low for a project with {file_count} route/page files. '
              f'Expected at least {min_tests_for_files} tests (2 per route file). '
              f'Agent reported {rf} routes/features but {file_count} route files were found independently.')
        sys.exit(1)

print('OK')
