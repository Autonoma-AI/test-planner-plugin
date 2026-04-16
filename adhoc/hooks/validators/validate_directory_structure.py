#!/usr/bin/env python3
"""Validates that the ad hoc focus folder is properly populated.

For the ad hoc planner the index lives at autonoma/qa-tests/{focus-slug}/INDEX.md.
We check that the focus folder contains at least one test file besides INDEX.md,
and that every subfolder declared in the index also has at least one .md file.
"""
import os
import sys
import glob as globmod
import yaml

filepath = sys.argv[1]  # autonoma/qa-tests/{focus-slug}/INDEX.md
focus_dir = os.path.dirname(filepath)  # autonoma/qa-tests/{focus-slug}/

# Parse the INDEX frontmatter to get declared folder names
content = open(filepath).read()
parts = content.split('---', 2)
try:
    fm = yaml.safe_load(parts[1]) if len(parts) >= 3 else {}
except Exception:
    fm = {}

declared_folders = [f.get('name') for f in fm.get('folders', []) if isinstance(f, dict) and f.get('name')]

# Focus folder must contain at least one test file (not INDEX.md)
test_files = [f for f in globmod.glob(os.path.join(focus_dir, '**', '*.md'), recursive=True)
              if os.path.basename(f) != 'INDEX.md']
if not test_files:
    print(f'Focus folder has no test files: {focus_dir}')
    sys.exit(1)

# Every declared subfolder must exist and contain at least one .md file
for name in declared_folders:
    subdir = os.path.join(focus_dir, name)
    if not os.path.isdir(subdir):
        print(f'Declared folder "{name}" does not exist: {subdir}')
        sys.exit(1)
    md_files = globmod.glob(os.path.join(subdir, '*.md'))
    if not md_files:
        print(f'Declared folder "{name}" has no .md files: {subdir}')
        sys.exit(1)

print('OK')
