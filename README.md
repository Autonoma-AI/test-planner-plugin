# Autonoma Test Planner

A Claude Code plugin that generates comprehensive E2E test suites for your codebase through a validated 6-step pipeline.

Each step runs in an isolated subagent with deterministic validation. The pipeline audits how application entities are created, implements an Autonoma Environment Factory against the target app, validates scenario lifecycles through the live endpoint, and only then generates E2E tests.

## Install

```text
/plugin marketplace add Autonoma-AI/test-planner-plugin
/plugin install autonoma-test-planner@autonoma
```

## Usage

Inside any project with Claude Code:

```text
/autonoma-test-planner:generate-tests
```

The full pipeline is interactive. After steps 1-5, Claude presents the step summary and waits for your confirmation before continuing.

Lifecycle reporting is hook-driven:

- `hooks/pipeline-kickoff.sh` creates the setup record and writes `autonoma/.docs-url` plus `autonoma/.generation-id`.
- `hooks/validate-pipeline-output.sh` validates artifacts, emits step events, uploads artifacts, and enforces the test-generation gate.
- `hooks/pretool-heartbeat.sh` keeps dashboard activity reporting alive while tools are running.

## Pipeline

### Step 1: Knowledge Base

Analyzes the app and produces `autonoma/AUTONOMA.md`, `autonoma/skills/*.md`, and `autonoma/features.json`.

**You review**: the core flows table.

### Step 2: Entity Creation Audit

Audits every database model and records how each model comes into existence in `autonoma/entity-audit.md`.

Models marked `independently_created: true` become Environment Factory factories that call the app's real creation functions. Dependent-only models use the SDK's raw SQL fallback and are torn down through their owner model.

**You review**: factory-backed models, dependent-only models, and any dual-creation models.

### Step 3: Scenarios

Reads the knowledge base and `autonoma/entity-audit.md`, then produces `autonoma/scenarios.md`.

Scenarios include `standard`, `empty`, and `large`, track variable fields that must vary across runs, and use nested create trees rooted at the scope entity.

**You review**: entity names, counts, relationships, variable fields, and via-owner versus standalone creation choices.

### Step 4: Implement Environment Factory

Installs and configures the Autonoma SDK endpoint, then registers a factory for every `independently_created: true` model from `entity-audit.md`.

This step runs a signed `discover` smoke test and factory-integrity checks, then writes `autonoma/.endpoint-implemented`. It does **not** run full `up` / `down`; lifecycle validation happens in Step 5.

**You review**: handler path, installed packages, factories registered, and required secrets.

### Step 5: Validate Scenario Lifecycle

Runs signed `discover` / `up` / `down` against every scenario. The validator may fix handler bugs or reconcile `autonoma/scenarios.md` with real endpoint behavior.

On success, it writes `autonoma/scenario-recipes.json`, `autonoma/.scenario-validation.json`, and `autonoma/.endpoint-validated`. The `.endpoint-validated` sentinel gates Step 6; test files cannot be written before it exists.

**You review**: scenarios passed, scenario edits, preflight result, and recipe upload status.

### Step 6: Generate E2E Tests

Generates markdown test files in `autonoma/qa-tests/` plus `autonoma/qa-tests/INDEX.md`.

**You review**: test distribution and coverage correlation.

## Key Outputs

- `autonoma/AUTONOMA.md`
- `autonoma/skills/*.md`
- `autonoma/features.json`
- `autonoma/entity-audit.md`
- `autonoma/scenarios.md`
- `autonoma/.factory-plan.md`
- `autonoma/.endpoint-implemented`
- `autonoma/scenario-recipes.json`
- `autonoma/.scenario-validation.json`
- `autonoma/.endpoint-validated`
- `autonoma/qa-tests/INDEX.md`

## Ad Hoc Test Generation

The same plugin includes a `generate-adhoc-tests` command that generates tests focused on a specific topic without regenerating your full test suite.

### Usage

Pass your focus description directly after the command:

```
/autonoma-test-planner:generate-adhoc-tests description
```

Or invoke without arguments and the command will suggest focus areas based on your codebase:

```
/autonoma-test-planner:generate-adhoc-tests
```

### How it works

**Subsequent runs** (active scenarios and recipes already exist in Autonoma): fetches existing scenario, skill, and test context from Autonoma, then runs only focused test generation for the requested topic.

Tests are written to `autonoma/qa-tests/{focus-slug}/` so they sit alongside your existing test suite without overwriting it.

### Running multiple focus areas

Each focus area run writes to its own subfolder and tracks its own generation ID file. Multiple topics can run in parallel:

```
autonoma/qa-tests/
├── canvas-interactions/      ← autonoma/.generation-id-canvas-interactions
└── signatures-and-documents/ ← autonoma/.generation-id-signatures-and-documents
```

## Environment Variables

Provide these before running the plugin:

```bash
AUTONOMA_DOCS_URL=<docs base url>
AUTONOMA_API_KEY=<api key>
AUTONOMA_PROJECT_ID=<application id>
AUTONOMA_API_URL=<setup api base url>
```

`AUTONOMA_DOCS_URL` is required so subagents can fetch the latest Autonoma instructions. `AUTONOMA_API_KEY`, `AUTONOMA_PROJECT_ID`, and `AUTONOMA_API_URL` are required for dashboard setup records, lifecycle events, artifact uploads, and recipe uploads.

The Environment Factory step generates or discovers these target-app values and updates `.env` and `.env.example` when applicable:

```bash
AUTONOMA_SHARED_SECRET=<shared hmac secret>
AUTONOMA_SIGNING_SECRET=<private signing secret>
```

`AUTONOMA_SDK_ENDPOINT` is needed by scenario validation and recipe preflight once the endpoint exists. Generated environment changes still need to be deployed with the target app.

## Validation

Every pipeline output is validated by shell-dispatched Python validators.

| File | Validator | Validation |
| --- | --- | --- |
| `AUTONOMA.md` | `validate_kb.py` | frontmatter and core-flow structure |
| `features.json` | `validate_features.py` | feature inventory schema |
| `entity-audit.md` | `validate_entity_audit.py` | model creation classification, factory counts, and owner links |
| `scenarios.md` | `validate_scenarios.py` | scenario schema and required sections |
| `.endpoint-implemented` | `validate_endpoint_implemented.py`, `validate_creation_file_immutable.py`, `validate_factory_fidelity.py` | handler path, factory integrity, immutable audit snapshot, and semantic factory fidelity |
| `.scenario-validation.json` | `validate_scenario_validation.py` | Step 5 terminal-state contract |
| `scenario-recipes.json` | `validate_scenario_recipes.py` | recipe schema plus live endpoint preflight |
| `INDEX.md` | `validate_test_index.py`, `validate_directory_structure.py` | test totals, folder breakdown, and directory structure |
| test files | `validate_test_file.py` | required frontmatter |

Test files are blocked until `autonoma/.endpoint-validated` exists.

## Local Development

```bash
claude --plugin-dir ./
claude plugin validate ./
pytest
```

## Project Structure

```text
autonoma-test-planner/
├── .claude-plugin/
├── commands/generate-tests.md
├── commands/generate-adhoc-tests.md
├── skills/generate-tests/SKILL.md
├── skills/generate-adhoc-tests/SKILL.md
├── agents/
│   ├── kb-generator.md
│   ├── entity-audit-generator.md
│   ├── scenario-generator.md
│   ├── env-factory-generator.md
│   ├── test-case-generator.md
│   ├── focused-test-case-generator.md
│   └── scenario-validator.md
├── hooks/
│   ├── pipeline-kickoff.sh
│   ├── pretool-heartbeat.sh
│   ├── transcript-streamer.py
│   ├── validate-pipeline-output.sh
│   ├── preflight_scenario_recipes.py
│   └── validators/
│       └── evals/
└── tests/
```

## License

MIT
