#!/usr/bin/env python3
"""Validates that the autonoma output directories are properly populated."""
import os
import sys
import glob as globmod

filepath = sys.argv[1]  # autonoma/qa-tests/INDEX.md

# Derive directory paths
qa_tests_dir = os.path.dirname(filepath)       # autonoma/qa-tests/
autonoma_dir = os.path.dirname(qa_tests_dir)   # autonoma/
skills_dir = os.path.join(autonoma_dir, 'skills')

# 1. qa-tests must have a "journey" subdirectory
journey_dir = os.path.join(qa_tests_dir, 'journey')
if not os.path.isdir(journey_dir):
    print(f'qa-tests is missing required "journey" subdirectory: {journey_dir}')
    sys.exit(1)

# 2. skills/ must exist and contain at least 1 .md file
if not os.path.isdir(skills_dir):
    print(f'skills directory not found: {skills_dir}')
    sys.exit(1)

skills_md = globmod.glob(os.path.join(skills_dir, '*.md'))
if len(skills_md) < 1:
    print(f'skills directory has no .md files: {skills_dir}')
    sys.exit(1)

# 3. qa-tests/ and every subdirectory must have at least 1 .md file (INDEX.md counts for qa-tests itself)
qa_md = globmod.glob(os.path.join(qa_tests_dir, '*.md'))
if len(qa_md) < 1:
    print(f'qa-tests directory has no .md files: {qa_tests_dir}')
    sys.exit(1)

for entry in sorted(os.listdir(qa_tests_dir)):
    subdir = os.path.join(qa_tests_dir, entry)
    if not os.path.isdir(subdir):
        continue
    md_files = globmod.glob(os.path.join(subdir, '*.md'))
    if len(md_files) < 1:
        print(f'qa-tests subdirectory "{entry}" has no .md files: {subdir}')
        sys.exit(1)

print('OK')
