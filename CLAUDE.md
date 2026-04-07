# Autonoma Test Planner Plugin

Claude Code plugin that generates E2E test suites through a 4-step deterministic pipeline.

## Project Structure

```
.claude-plugin/           # Plugin manifest (plugin.json, marketplace.json)
commands/generate-tests.md  # Entry point — dispatches the 4-step pipeline
skills/generate-tests/SKILL.md  # Orchestrator skill
agents/                   # Isolated subagents (one per step)
  kb-generator.md         # Step 1: Knowledge base → autonoma/AUTONOMA.md + features.json
  scenario-generator.md   # Step 2: Scenarios → autonoma/scenarios.md
  test-case-generator.md  # Step 3: Tests → autonoma/qa-tests/INDEX.md + test files
  env-factory-generator.md # Step 4: Environment factory endpoint
hooks/
  hooks.json              # PostToolUse hook config (triggers on Write)
  validate-pipeline-output.sh  # Bash dispatcher → routes to Python validators
  validators/             # Python scripts that validate YAML frontmatter
```

## How the Pipeline Works

Each step spawns an isolated subagent. After each Write, the PostToolUse hook in `hooks/hooks.json` runs `validate-pipeline-output.sh`, which pattern-matches the file path and runs the appropriate Python validator. Validators exit 0 (OK) or 2 (block with error message).

Steps auto-advance — no inter-step confirmation prompts. Step 4 is the final step.

## Validation

Validators are in `hooks/validators/`. They parse YAML frontmatter and check required fields, types, and cross-file consistency. All validators print "OK" on success or an error message on failure.

| Validator | File matched | Key checks |
|-----------|-------------|------------|
| `validate_kb.py` | `*/autonoma/AUTONOMA.md` | app_name, app_description (≥20 chars), core_flows with at least one `core: true` |
| `validate_features.py` | `*/autonoma/features.json` | features array length matches total_features, valid types, at least one core feature |
| `validate_scenarios.py` | `*/autonoma/scenarios.md` | scenario_count ≥ 3, standard/empty/large scenarios present, entity_types |
| `validate_test_index.py` | `*/autonoma/qa-tests/INDEX.md` | test totals match folder sums, criticality sums, cross-checks against features.json |
| `validate_test_file.py` | `*/autonoma/qa-tests/*/[!I]*.md` | title, description, criticality (critical/high/mid/low), scenario, flow |

## Development

```bash
# Run plugin locally without installing
claude --plugin-dir ./

# Validate plugin structure
claude plugin validate ./
```

## Dependencies

- Python 3 + PyYAML (auto-installed by the hook if missing)

