---
name: generate-tests
description: >
  Generates E2E test cases for a codebase through a validated multi-step pipeline.
  Each step runs in an isolated subagent and must pass deterministic validation
  before the next step begins. Use when the user wants to generate tests, create
  test scenarios, or build a test suite for their project.
---

# Autonoma E2E Test Generation Pipeline

You are orchestrating a 4-step test generation pipeline. Each step runs as an isolated subagent.
**Every step MUST complete successfully and pass validation before the next step begins.**
Do NOT skip steps. Do NOT proceed if validation fails.

## Before Starting

Create the output directory:
```bash
mkdir -p autonoma/skills autonoma/qa-tests
```

## Step 1: Generate Knowledge Base

Spawn the `kb-generator` subagent with the following task:

> Analyze the codebase and generate the knowledge base. Write the output to `autonoma/AUTONOMA.md`
> and create skill files in `autonoma/skills/`. The file MUST have YAML frontmatter with
> app_name, app_description, core_flows (feature/description/core table), feature_count, and skill_count.
> Fetch the latest instructions from https://docs.agent.autonoma.app/llms/test-planner/step-1-knowledge-base.txt first.

**After the subagent completes:**
1. Verify `autonoma/AUTONOMA.md` exists and is non-empty
2. The PostToolUse hook will have validated the frontmatter format automatically
3. Read the file and present the frontmatter to the user — specifically the core_flows table
4. Ask the user: "Does this core flows table look correct? These flows determine how the test budget is distributed. Please confirm or suggest changes before I proceed to Step 2."
5. **Do NOT proceed until the user confirms.**

## Step 2: Generate Scenarios

Spawn the `scenario-generator` subagent with the following task:

> Read the knowledge base from `autonoma/AUTONOMA.md` and `autonoma/skills/`.
> Generate test data scenarios. Write the output to `autonoma/scenarios.md`.
> The file MUST have YAML frontmatter with scenario_count, scenarios summary, and entity_types.
> Fetch the latest instructions from https://docs.agent.autonoma.app/llms/test-planner/step-2-scenarios.txt first.

**After the subagent completes:**
1. Verify `autonoma/scenarios.md` exists and is non-empty
2. The PostToolUse hook will have validated the frontmatter format automatically
3. Read the file and present the frontmatter summary to the user — scenario names, entity counts, entity types
4. Ask the user: "Do these scenarios look correct? The standard scenario data becomes hard assertions in your tests. Please confirm or suggest changes before I proceed to Step 3."
5. **Do NOT proceed until the user confirms.**

## Step 3: Generate E2E Test Cases

Spawn the `test-case-generator` subagent with the following task:

> Read the knowledge base from `autonoma/AUTONOMA.md`, skills from `autonoma/skills/`,
> and scenarios from `autonoma/scenarios.md`.
> Generate complete E2E test cases as markdown files in `autonoma/qa-tests/`.
> You MUST create `autonoma/qa-tests/INDEX.md` with frontmatter containing total_tests,
> total_folders, folder breakdown, and coverage_correlation.
> Each test file MUST have frontmatter with title, description, criticality, scenario, and flow.
> Fetch the latest instructions from https://docs.agent.autonoma.app/llms/test-planner/step-3-e2e-tests.txt first.

**After the subagent completes:**
1. Verify `autonoma/qa-tests/INDEX.md` exists and is non-empty
2. The PostToolUse hook will have validated the INDEX frontmatter and individual test file frontmatter
3. Read the INDEX.md and present the summary to the user — total tests, folder breakdown, coverage correlation
4. Ask the user: "Does this test distribution look correct? The total test count should roughly correlate with the number of routes/features in your app. Please confirm or suggest changes before I proceed to Step 4."
5. **Do NOT proceed until the user confirms.**

## Step 4: Implement Environment Factory

Spawn the `env-factory-generator` subagent with the following task:

> Read the scenarios from `autonoma/scenarios.md` and implement the Autonoma Environment Factory
> endpoint in the project's backend. The endpoint handles discover/up/down actions.
> Fetch the latest instructions from https://docs.agent.autonoma.app/llms/test-planner/step-4-implement-scenarios.txt
> and https://docs.agent.autonoma.app/llms/guides/environment-factory.txt first.
> After implementing, run integration tests to verify the endpoint works.
> Use AUTONOMA_SIGNING_SECRET and AUTONOMA_JWT_SECRET as environment variable names.

**After the subagent completes:**
1. Verify the endpoint was created and tests pass
2. Present the results to the user — what was implemented, where, test results
3. Report any issues that need manual attention

## Completion

After all steps complete, summarize:
- **Step 1**: Knowledge base location and core flow count
- **Step 2**: Scenario count and entity types covered
- **Step 3**: Total test count, folder breakdown, coverage correlation
- **Step 4**: Endpoint location, test results, env var setup instructions
