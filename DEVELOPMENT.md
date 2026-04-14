# Development Setup

This guide explains how to test changes from a branch without publishing to the marketplace.

## Prerequisites

- [Claude Code](https://claude.ai/code)
- your branch pushed to GitHub

## Install from a branch

```text
/plugin uninstall autonoma-test-planner
/plugin marketplace remove autonoma
/plugin marketplace add https://github.com/Autonoma-AI/test-planner-plugin#your-branch-name
/plugin install autonoma-test-planner@autonoma
```

## Updating after changes

```text
/plugin uninstall autonoma-test-planner
/plugin marketplace remove autonoma
/plugin marketplace add https://github.com/Autonoma-AI/test-planner-plugin#your-branch-name
/plugin install autonoma-test-planner@autonoma
```

## Environment variables

The plugin itself requires these values in the target project session:

| Variable | Description |
| --- | --- |
| `AUTONOMA_API_KEY` | Autonoma API key |
| `AUTONOMA_PROJECT_ID` | Application ID from the Autonoma dashboard |
| `AUTONOMA_API_URL` | API base URL, for example `http://localhost:4000` in local dev |

You do **not** need to pre-set `AUTONOMA_SDK_ENDPOINT`, `AUTONOMA_SHARED_SECRET`, or `AUTONOMA_SIGNING_SECRET`.
Step 1 creates or discovers those values in the target repo by editing `.env` and `.env.example`.

If you want the pipeline to pause for review after Steps 1-4 while testing, set
`AUTONOMA_REQUIRE_CONFIRMATION=true` in the Claude Code session.

After the generated PR is merged, the user still needs to deploy those env changes.

## References

- [Claude Code — Discover and install plugins](https://code.claude.com/docs/en/discover-plugins#add-from-github)
