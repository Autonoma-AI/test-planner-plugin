# Local Development Setup

This guide explains how to install the plugin locally from source so you can test changes without publishing to the marketplace.

## Prerequisites

- [Claude Code](https://claude.ai/code) installed
- The branch cloned locally

## Install

Copy the command file to your Claude commands directory:

```bash
cp ~/repos/test-planner-plugin/commands/generate-tests.md ~/.claude/commands/autonoma-generate-tests.md
```

That's it. Claude Code picks up any file in `~/.claude/commands/` automatically - no restart needed.

## Verify

Open any project in Claude Code and run:

```
/autonoma-generate-tests
```

You should see the command in the autocomplete list.

## Updating after changes

The `~/.claude/commands/` file is a static copy - it does not sync automatically. After pulling new changes or editing the source, re-run the copy command:

```bash
cp ~/repos/test-planner-plugin/commands/generate-tests.md ~/.claude/commands/autonoma-generate-tests.md
```

## Environment variables

The plugin requires three environment variables to be set in the project where you run it:

| Variable | Description |
| --- | --- |
| `AUTONOMA_API_KEY` | Your Autonoma API key (get it from the dashboard under Settings > API Keys) |
| `AUTONOMA_PROJECT_ID` | The application ID from the Autonoma dashboard |
| `AUTONOMA_API_URL` | API base URL - use `http://localhost:4000` for local dev |

Add them to the `.env` file or export them in your shell before running Claude Code in the target project.

## How the naming works

The file `~/.claude/commands/autonoma-generate-tests.md` is invoked as `/autonoma-generate-tests`. The marketplace install uses the namespace `autonoma-test-planner:generate-tests`, but for local development the flat name is sufficient.
