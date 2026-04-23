# Autonoma Test Planner Plugin

Claude Code plugin that generates E2E test suites through a deterministic multi-step pipeline.

## Project Structure

```text
.claude-plugin/              # Plugin manifest
commands/generate-tests.md   # Full pipeline command
commands/generate-adhoc-tests.md
skills/generate-tests/SKILL.md
skills/generate-adhoc-tests/SKILL.md
agents/
  kb-generator.md              # Step 1: Knowledge base
  entity-audit-generator.md    # Step 2: Entity creation audit
  scenario-generator.md        # Step 3: Scenarios
  env-factory-generator.md     # Step 4: Environment Factory implementation
  scenario-validator.md        # Step 5: Scenario lifecycle validation
  test-case-generator.md       # Step 6: E2E tests
  focused-test-case-generator.md
hooks/
  hooks.json
  pipeline-kickoff.sh
  pretool-heartbeat.sh
  transcript-streamer.py
  validate-pipeline-output.sh
  preflight_scenario_recipes.py
  validators/
    evals/
tests/
```

## Pipeline

1. Knowledge Base
2. Entity Creation Audit
3. Scenarios
4. Implement Environment Factory
5. Validate Scenario Lifecycle
6. Generate E2E Tests

The full pipeline is interactive. After steps 1-5, Claude presents the step summary and waits for user confirmation before continuing. Lifecycle reporting is handled by plugin hooks, not by ad hoc agent curl calls.

## Validation

Validators are in `hooks/validators/`.

| Validator | File matched | Key checks |
|-----------|-------------|------------|
| `validate_kb.py` | `*/autonoma/AUTONOMA.md` | frontmatter and core-flow structure |
| `validate_features.py` | `*/autonoma/features.json` | feature inventory schema |
| `validate_entity_audit.py` | `*/autonoma/entity-audit.md` | model creation classification and owner links |
| `validate_scenarios.py` | `*/autonoma/scenarios.md` | scenario count, metadata, required sections |
| `validate_endpoint_implemented.py` | `*/autonoma/.endpoint-implemented` | handler path and factory integrity |
| `validate_creation_file_immutable.py` | `*/autonoma/.endpoint-implemented` | accepted audit creation files were not rewritten unsafely |
| `validate_factory_fidelity.py` | `*/autonoma/.endpoint-implemented` | semantic per-model factory fidelity |
| `validate_scenario_validation.py` | `*/autonoma/.scenario-validation.json` | Step 5 terminal-state contract |
| `validate_scenario_recipes.py` | `*/autonoma/scenario-recipes.json` | recipe schema |
| `validate_test_index.py` | `*/autonoma/qa-tests/INDEX.md` | test totals and folder sums |
| `validate_directory_structure.py` | `*/autonoma/qa-tests/INDEX.md` | test directory structure |
| `validate_test_file.py` | `*/autonoma/qa-tests/*/[!I]*.md` | test frontmatter |

Scenario recipes also run live endpoint preflight through `hooks/preflight_scenario_recipes.py`.

Test file writes are blocked until `autonoma/.endpoint-validated` exists.

## Development

```bash
claude --plugin-dir ./
claude plugin validate ./
pytest
```

## Notes

- Step 4 implements the Environment Factory and may edit target backend code.
- Step 4 writes `autonoma/.endpoint-implemented` only after discover smoke and factory-integrity checks pass.
- Step 5 validates signed `discover` / `up` / `down` for every scenario and may fix handler bugs or reconcile `scenarios.md`.
- Step 6 is gated on `autonoma/.endpoint-validated`.
