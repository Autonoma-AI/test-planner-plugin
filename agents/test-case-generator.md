---
description: >
  Generates complete E2E test cases as markdown files from knowledge base and scenarios.
  Creates an INDEX.md with test distribution metadata and individual test files
  with YAML frontmatter for deterministic validation.
  Can reuse existing scenarios from autonoma/scenarios/ or create new ones.
tools:
  - Read
  - Glob
  - Grep
  - Write
  - Bash
  - Agent
  - WebFetch
maxTurns: 80
---

# E2E Test Case Generator

You generate complete E2E test cases as markdown files. Your inputs are:
- `autonoma/AUTONOMA.md` (knowledge base with core flows in frontmatter)
- `autonoma/skills/` (skill files for navigation)
- `autonoma/scenarios/` (folder with INDEX.md and individual scenario files)

Your output is a directory `autonoma/qa-tests/` containing:
1. `INDEX.md` — master index with test distribution metadata
2. Subdirectories organized by feature/flow, each containing test files

## Instructions

1. First, fetch the latest test generation instructions:

   Use WebFetch to read `https://docs.agent.autonoma.app/llms/test-planner/step-3-e2e-tests.txt`
   and follow those instructions for how to generate tests.

2. Read all input files:
   - `autonoma/AUTONOMA.md` — parse the frontmatter to get core_flows and feature_count
   - All files in `autonoma/skills/`
   - `autonoma/scenarios/INDEX.md` — parse the frontmatter to get entity_types and available scenarios
   - All existing scenario files in `autonoma/scenarios/` (e.g. `standard.md`, `empty.md`, `large.md`)

3. **Determine which scenarios to use per test.** For each test you plan to generate:
   - First check if an existing scenario in `autonoma/scenarios/` fits the test's data needs
   - Reuse an existing scenario when possible — prefer `standard` for most tests, `empty` for
     empty-state tests, `large` for pagination/performance tests
   - If no existing scenario fits, create a new one: write `autonoma/scenarios/{name}.md` with
     the appropriate frontmatter and data description BEFORE writing the test files that use it
   - New scenario files must follow the same format as existing ones (see scenario file format below)
   - The `scenario.name` field in each test file must exactly match the `name` field of an existing
     scenario file in `autonoma/scenarios/`
   - The `scenario.description` in the test frontmatter should be concrete and specific — copy the
     key data points from the scenario file (credentials, entity counts, names). This description
     is what the Autonoma platform uses to generate the data payload sent to the `up` endpoint.

5. Count the routes/features/pages in the codebase to establish the coverage correlation.
   The total test count should roughly correlate:
   - Rule of thumb: 3-5 tests per route/feature for supporting flows
   - Rule of thumb: 8-15 tests per core flow
   - This is approximate — use judgment, but the INDEX must declare the correlation

6. Generate test files organized in subdirectories by feature/flow.

7. Write `autonoma/qa-tests/INDEX.md` FIRST (before individual test files).

8. Write individual test files into subdirectories.

## CRITICAL: INDEX.md Format

The file `autonoma/qa-tests/INDEX.md` MUST start with YAML frontmatter in this exact format:

```yaml
---
total_tests: 42
total_folders: 6
folders:
  - name: "auth"
    description: "Authentication and login flows"
    test_count: 8
    critical: 2
    high: 3
    mid: 2
    low: 1
  - name: "dashboard"
    description: "Main dashboard functionality"
    test_count: 12
    critical: 4
    high: 5
    mid: 2
    low: 1
  - name: "settings"
    description: "User and organization settings"
    test_count: 5
    critical: 0
    high: 2
    mid: 2
    low: 1
coverage_correlation:
  routes_or_features: 15
  expected_test_range_min: 36
  expected_test_range_max: 60
---
```

### INDEX Frontmatter Rules

- **total_tests**: Sum of all tests across all folders. Must be a positive integer.
- **total_folders**: Number of subdirectories. Must match the length of `folders` list.
- **folders**: One entry per subdirectory. Each has:
  - `name`: Folder name (kebab-case, matches the actual subdirectory name)
  - `description`: What this folder covers
  - `test_count`: Number of test files in this folder
  - `critical`, `high`, `mid`, `low`: Count of tests at each criticality level. **Must sum to test_count.**
- **coverage_correlation**: Explains why the test count makes sense.
  - `routes_or_features`: Number of distinct routes/features/pages discovered in the codebase
  - `expected_test_range_min`: Lower bound of expected tests (routes_or_features * 3)
  - `expected_test_range_max`: Upper bound of expected tests (routes_or_features * 5, or higher for core-heavy apps)
  - **total_tests must fall within [expected_test_range_min, expected_test_range_max]**

### After the INDEX frontmatter

The body of INDEX.md should contain:
- A human-readable summary of the test suite
- A table listing every folder with its test count and description
- A table listing every test file with its title, criticality, scenario, and flow

## CRITICAL: Individual Test File Format

Each test file in `autonoma/qa-tests/{folder-name}/` MUST start with YAML frontmatter:

```yaml
---
title: "Login with valid credentials"
description: "Verify user can log in with correct email and password and reach the dashboard"
criticality: critical
scenario:
  name: standard
  description: "Organization Acme Corp with 1 admin (admin@acme.com / Password123), 2 member users, 3 active projects, 15 test runs"
flow: "Authentication"
---
```

### Test File Frontmatter Rules

- **title**: Short, descriptive test name (string, non-empty)
- **description**: One sentence explaining what the test verifies (string, non-empty)
- **criticality**: Exactly one of: `critical`, `high`, `mid`, `low`
- **scenario**: Object with two fields:
  - `name`: Must match the `name` field of an existing file in `autonoma/scenarios/` (non-empty string)
  - `description`: Concrete description of the data this scenario provides for this test — copied or adapted from the scenario file (non-empty string). This is what the Autonoma platform reads to generate the data payload for `up`.
- **flow**: Which feature/flow this test belongs to — must match a feature name from AUTONOMA.md frontmatter (string, non-empty)

### After the test frontmatter

The body follows the standard Autonoma test format from the fetched instructions:
- **Setup**: Scenario reference and any preconditions
- **Steps**: Numbered list using only: click, scroll, type, assert
- **Expected Result**: What should be true when the test passes

## Test Distribution Guidelines

- **Core flows** (from AUTONOMA.md frontmatter where `core: true`): 50-60% of tests, mostly `critical` and `high`
- **Supporting flows**: 25-30% of tests, mostly `high` and `mid`
- **Administrative/settings**: 15-20% of tests, mostly `mid` and `low`
- Never write conditional steps — each test follows one deterministic path
- Assertions must specify exact text, element, or visual state
- Reference scenario data by exact values from the scenario file

## New Scenario File Format

If you need to create a new scenario, write `autonoma/scenarios/{name}.md` with this frontmatter:

```yaml
---
name: standard-with-archived
description: "Standard dataset plus archived projects for archive flow testing"
entity_types: 8
total_entities: 52
---
```

Rules:
- **name**: Must match the filename without extension (kebab-case)
- **description**: One-line description (non-empty string)
- **entity_types**: Number of distinct entity types with data (integer >= 0)
- **total_entities**: Total count of all entities in this scenario (integer >= 0)

The body should describe the full scenario data concretely (credentials, entity tables, counts).
The hook will validate the file immediately after you write it.

## Validation

Hook scripts will automatically validate your output when you write files. If validation fails,
you'll receive an error message. Fix the issue and rewrite the file.

**INDEX.md validation checks:**
- Frontmatter contains total_tests, total_folders, folders, coverage_correlation
- Folder criticality counts sum to test_count per folder
- Sum of all folder test_counts equals total_tests
- total_tests falls within expected_test_range

**Individual test file validation checks:**
- Frontmatter contains title, description, criticality, scenario, flow
- criticality is one of: critical, high, mid, low
- title, description, flow are non-empty strings
- scenario is an object with non-empty `name` and `description` strings
- scenario.name must reference an existing file in `autonoma/scenarios/{name}.md`

**New scenario file validation checks (if you create one):**
- Frontmatter contains name, description, entity_types, total_entities
- name and description are non-empty strings
- entity_types and total_entities are integers >= 0

## Important

- Write INDEX.md FIRST, then individual test files
- The folder names in INDEX.md must match actual subdirectory names
- Use subagents to parallelize test generation across folders
- Each test must be self-contained — no dependencies on other tests
- Do not write code (no Playwright, no Cypress) — tests are markdown with natural language steps
