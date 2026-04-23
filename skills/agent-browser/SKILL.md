---
name: agent-browser
description: >
  Full CLI reference for agent-browser, a headless browser automation tool
  for AI agents. Use this skill when driving a browser via Bash to navigate,
  interact with elements, manage cookies/storage, and verify page state.
---

# agent-browser CLI Reference

`agent-browser` is a fast, headless-by-default browser automation CLI built
for AI agents. It uses Playwright under the hood, exposed as simple shell
commands with `--json` output.

Install: `npm install -g agent-browser && agent-browser install`

## Global Options (apply to all commands)

| Flag | Description |
|------|-------------|
| `--session <name>` | Isolated browser session (or `AGENT_BROWSER_SESSION` env) |
| `--json` | JSON output (`{"success": bool, "data": ..., "error": ...}`) |
| `--headed` | Show browser window (default is headless) |
| `--headers <json>` | HTTP headers scoped to the URL's origin (for auth) |
| `--cdp <port>` | Connect via Chrome DevTools Protocol |

**Always use `--json`** for machine-readable output.
**Always use `--session <name>`** to avoid session conflicts.
**Never use `--headed`** in automated pipelines.

## Core Commands

### Navigation

```bash
agent-browser open <url>                  # Navigate to URL
agent-browser open <url> --headers '{"Authorization": "Bearer ..."}'
agent-browser back                        # Go back
agent-browser forward                     # Go forward
agent-browser reload                      # Reload page
```

`open` auto-prepends `https://` if no protocol given. Headers are scoped to
that origin only.

### Interaction

```bash
agent-browser click <selector>            # Click element (CSS, XPath, or @ref)
agent-browser dblclick <selector>         # Double-click
agent-browser fill <selector> <text>      # Clear + fill input
agent-browser type <selector> <text>      # Type without clearing
agent-browser press <key>                 # Press key (Enter, Tab, Control+a)
agent-browser hover <selector>            # Hover element
agent-browser focus <selector>            # Focus element
agent-browser check <selector>            # Check checkbox
agent-browser uncheck <selector>          # Uncheck checkbox
agent-browser select <selector> <value>   # Select dropdown option
agent-browser upload <selector> <files>   # Upload files
agent-browser scroll <dir> [px]           # Scroll (up/down/left/right)
agent-browser scrollintoview <selector>   # Scroll element into view
```

Selectors can be CSS (`"#id"`, `".class"`), XPath (`"//button"`), or
element refs from `snapshot` (`@e1`, `@e2`).

### Getting Information

```bash
agent-browser get text <selector>         # Text content
agent-browser get html <selector>         # Inner HTML
agent-browser get value <selector>        # Input value
agent-browser get attr <selector> <name>  # Attribute value
agent-browser get title                   # Page title
agent-browser get url                     # Current URL
agent-browser get count <selector>        # Count matching elements
agent-browser get box <selector>          # Bounding box
```

### State Checks

```bash
agent-browser is visible <selector>       # true/false
agent-browser is enabled <selector>
agent-browser is checked <selector>
```

### Finding Elements (semantic locators)

```bash
agent-browser find role <role> click              # By ARIA role
agent-browser find role button click --name Submit
agent-browser find text "Sign in" click           # By visible text
agent-browser find label "Email" fill "user@x.com"
agent-browser find placeholder "Password" fill "secret"
agent-browser find testid "login-btn" click       # By data-testid
agent-browser find first "input" fill "value"     # First match
agent-browser find nth 2 "li" click               # Nth match (0-based)
```

Options: `--name <n>` (filter role by name), `--exact` (exact text match).

### Snapshots & Screenshots

```bash
agent-browser snapshot                    # Accessibility tree with @refs
agent-browser snapshot -i                 # Interactive elements only
agent-browser snapshot -c                 # Compact (remove empty nodes)
agent-browser snapshot -d 3               # Limit depth
agent-browser snapshot -s "#main"         # Scope to CSS selector

agent-browser screenshot [path]           # Screenshot (base64 if no path)
agent-browser screenshot ./shot.png
agent-browser screenshot --full ./full.png  # Full page
agent-browser pdf <path>                  # Save as PDF
```

**Use `snapshot -i` to discover form fields** — it shows element refs
(`@e1`, `@e2`) you can use in subsequent `fill`, `click` commands.

### Cookies & Storage

```bash
agent-browser cookies                     # Get all cookies
agent-browser cookies get                 # Same
agent-browser cookies set <name> <value>  # Set cookie (current context)
agent-browser cookies clear               # Clear all

agent-browser storage local               # Get all localStorage
agent-browser storage local get <key>
agent-browser storage local set <key> <value>
agent-browser storage local clear
agent-browser storage session get <key>   # sessionStorage
```

**Important**: `cookies set` scopes to the current page context. Navigate to
the target origin first before setting cookies.

### JavaScript Evaluation

```bash
agent-browser eval "document.title"
agent-browser eval "document.cookie='name=value; path=/; domain=localhost'"
agent-browser eval "window.location.href"
```

Use `eval` with `document.cookie=` when you need to set cookie attributes
(path, domain, SameSite, Secure, HttpOnly) that `cookies set` doesn't expose.

### Waiting

```bash
agent-browser wait <selector>             # Wait for element
agent-browser wait 2000                   # Wait ms
agent-browser wait --url "**/dashboard"   # Wait for URL match
agent-browser wait --load networkidle     # Wait for load state
agent-browser wait --fn "window.ready"    # Wait for JS expression
agent-browser wait --text "Welcome"       # Wait for text
```

### Network

```bash
agent-browser network route "**/api/*" --abort     # Block requests
agent-browser network route "**/data" --body '{"mock": true}'
agent-browser network unroute                      # Remove routes
agent-browser network requests                     # List requests
agent-browser network requests --filter "api"
```

### Browser Settings

```bash
agent-browser set viewport 1920 1080
agent-browser set device "iPhone 12"
agent-browser set headers '{"X-Custom": "value"}'
agent-browser set credentials <user> <pass>   # HTTP auth
agent-browser set media dark
agent-browser set offline on
```

### Tabs

```bash
agent-browser tab list
agent-browser tab new
agent-browser tab close
agent-browser tab 2                       # Switch to tab
```

### Session Management

```bash
agent-browser session                     # Show current session
agent-browser session list                # List active sessions
agent-browser close                       # Close browser & session
```

### Debug

```bash
agent-browser console                     # View console logs
agent-browser errors                      # View page errors
agent-browser highlight <selector>        # Highlight element
agent-browser trace start                 # Record trace
agent-browser trace stop [path]
```

## JSON Output Format

All commands with `--json` return:

```json
{"success": true,  "data": <command-specific>, "error": null}
{"success": false, "data": null, "error": "error message"}
```

Examples:
- `get url` → `{"success": true, "data": {"url": "https://..."}, "error": null}`
- `cookies get` → `{"success": true, "data": {"cookies": [...]}, "error": null}`
- `snapshot` → `{"success": true, "data": {"snapshot": "..."}, "error": null}`

## Common Patterns

### Set cookie and verify protected page

```bash
agent-browser --session s1 --json open http://localhost:3000/login
agent-browser --session s1 --json cookies set session "abc123"
agent-browser --session s1 --json open http://localhost:3000/dashboard
agent-browser --session s1 --json get url    # check not redirected
agent-browser --session s1 --json get text body  # check marker text
agent-browser --session s1 screenshot ./proof.png
agent-browser --session s1 close
```

### Fill login form using snapshot

```bash
agent-browser --session s1 --json open http://localhost:3000/login
agent-browser --session s1 snapshot -i       # find form field refs
agent-browser --session s1 --json fill @e1 "user@example.com"
agent-browser --session s1 --json fill @e2 "password123"
agent-browser --session s1 --json click @e3  # submit button
agent-browser --session s1 --json wait --url "**/dashboard"
agent-browser --session s1 --json get url
agent-browser --session s1 close
```

### Auth via headers

```bash
agent-browser --session s1 --json open http://localhost:3000/dashboard \
  --headers '{"Authorization": "Bearer eyJ..."}'
agent-browser --session s1 --json get url
agent-browser --session s1 close
```
