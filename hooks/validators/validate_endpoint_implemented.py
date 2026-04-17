#!/usr/bin/env python3
"""Validator for autonoma/.endpoint-implemented.

Blocks the sentinel write when the handler file contains an inline ORM write
inside a defineFactory({ create }) body for a model the entity audit marked
has_creation_code: true. This is the #1 bug the env-factory agent ships and
the agent's self-policing factory-integrity check has proven insufficient.

Inputs: path to .endpoint-implemented (via validate-pipeline-output.sh).
Reads:
  - autonoma/entity-audit.md (frontmatter: models with has_creation_code true/false)
  - the handler file path recorded in .endpoint-implemented body (first match of "handler: <path>")

Exit codes:
  0 — clean
  2 — anti-pattern found; prints a Claude-facing error message on stderr

The regex set mirrors the language list in agents/env-factory-generator.md's
"The one thing you MUST NOT do" section. Raw SQL literal INSERTs are not
matched here because distinguishing them from teardown DELETE strings in the
same factory block requires full parsing — the grep-level anti-pattern
detection catches the >95% case.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import yaml  # type: ignore

SENTINEL_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

# Anti-pattern: ORM create/insert/upsert calls that almost certainly belong to
# a raw ORM write rather than a service/repository method call.
ORM_ANTI_PATTERN = re.compile(
    r"\b(prisma|db|tx|ctx\.executor)\."        # ORM root
    r"[a-zA-Z_][a-zA-Z0-9_]*\."                # model accessor
    r"(create|createMany|insert|insertMany|upsert)\s*\(",
    re.IGNORECASE,
)

# A second class: Drizzle-style `tx.insert(xTable)` / `db.insert(xTable)`.
DRIZZLE_INSERT = re.compile(
    r"\b(tx|db|ctx\.executor)\.insert\s*\(",
)

FACTORY_HEADER = re.compile(
    r"([A-Z][A-Za-z0-9_]*)\s*:\s*defineFactory\s*\(\s*\{",
)


def fail(message: str) -> None:
    sys.stderr.write(message + "\n")
    sys.exit(2)


def find_matching_brace(src: str, open_idx: int) -> int:
    """Given index of `{`, return index of matching `}`.

    Naive balancer — ignores strings/comments. Good enough for generated
    handler files that follow the standard shape.
    """
    depth = 0
    i = open_idx
    n = len(src)
    while i < n:
        c = src[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def extract_factory_bodies(src: str) -> list[tuple[str, str]]:
    """Return list of (model_name, factory_inner_src)."""
    out: list[tuple[str, str]] = []
    for m in FACTORY_HEADER.finditer(src):
        model = m.group(1)
        brace_open = src.find("{", m.end() - 1)
        if brace_open < 0:
            continue
        brace_close = find_matching_brace(src, brace_open)
        if brace_close < 0:
            continue
        out.append((model, src[brace_open + 1 : brace_close]))
    return out


def extract_create_body(factory_src: str) -> str:
    """Find the `create:` or `create(` body inside a factory config object."""
    # Pattern: create(data, ctx) { ... }  OR  create: async (data, ctx) => { ... }
    # OR create: (data, ctx) => { ... }
    create_start = re.search(r"\bcreate\s*[(:]", factory_src)
    if not create_start:
        return ""
    # Find the first `{` after create_start.
    brace_open = factory_src.find("{", create_start.end())
    if brace_open < 0:
        return ""
    brace_close = find_matching_brace(factory_src, brace_open)
    if brace_close < 0:
        return ""
    return factory_src[brace_open + 1 : brace_close]


def parse_audit() -> dict[str, bool]:
    """Return {model_name: has_creation_code}."""
    audit_path = Path("autonoma/entity-audit.md")
    if not audit_path.exists():
        fail("Missing autonoma/entity-audit.md — cannot verify factory integrity.")
    text = audit_path.read_text()
    if not text.startswith("---"):
        fail("autonoma/entity-audit.md missing YAML frontmatter.")
    end = text.find("\n---", 3)
    if end < 0:
        fail("autonoma/entity-audit.md frontmatter not terminated.")
    try:
        fm = yaml.safe_load(text[3:end])
    except yaml.YAMLError as e:
        fail(f"autonoma/entity-audit.md frontmatter not valid YAML: {e}")
    models = fm.get("models") or []
    out: dict[str, bool] = {}
    for entry in models:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or entry.get("model")
        if not name:
            continue
        out[str(name)] = bool(entry.get("has_creation_code"))
    return out


def resolve_handler_path() -> Path:
    """Read the handler path recorded in .endpoint-implemented body."""
    if not SENTINEL_PATH or not Path(SENTINEL_PATH).exists():
        fail(".endpoint-implemented sentinel path not provided or missing.")
    body = Path(SENTINEL_PATH).read_text()

    candidates: list[str] = []
    m = re.search(r"handler:\s*(\S+)", body, re.IGNORECASE)
    if m:
        candidates.append(m.group(1).rstrip(".,;:"))
    # Fallback: extract every path-looking token ending in a source extension.
    for tok in re.findall(r"[\w./\\-]+\.(?:ts|tsx|js|mjs|cjs|py|rb|php|java|go|rs|ex|exs)", body):
        candidates.append(tok.rstrip(".,;:"))

    seen: set[str] = set()
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        p = Path(cand)
        if not p.is_absolute():
            p = Path.cwd() / cand
        if p.exists() and p.is_file():
            return p

    fail(
        ".endpoint-implemented body must name the handler file (e.g. a line "
        "'handler: apps/api/src/routes/autonoma/autonoma.handler.ts') so the "
        "factory-integrity validator can locate it. Checked: "
        + ", ".join(candidates[:8] or ["(no path tokens found)"])
    )
    return Path()  # unreachable


def main() -> None:
    audit = parse_audit()
    handler_path = resolve_handler_path()
    src = handler_path.read_text()

    violations: list[tuple[str, int, str]] = []
    factories = extract_factory_bodies(src)

    seen_models: set[str] = set()
    for model, factory_src in factories:
        seen_models.add(model)
        if not audit.get(model):
            # has_creation_code: false or unknown — ORM fallback is legitimate.
            continue
        create_body = extract_create_body(factory_src)
        if not create_body:
            continue
        for m in ORM_ANTI_PATTERN.finditer(create_body):
            line_no = create_body[: m.start()].count("\n") + 1
            snippet = create_body.splitlines()[line_no - 1].strip()
            violations.append((model, line_no, snippet))
        for m in DRIZZLE_INSERT.finditer(create_body):
            line_no = create_body[: m.start()].count("\n") + 1
            snippet = create_body.splitlines()[line_no - 1].strip()
            violations.append((model, line_no, snippet))

    # Flag audited models missing a factory entirely.
    missing_factories = [
        name for name, has_code in audit.items() if has_code and name not in seen_models
    ]

    if not violations and not missing_factories:
        sys.exit(0)

    lines = [
        "FACTORY INTEGRITY CHECK FAILED — .endpoint-implemented will NOT be written.",
        "",
        f"Handler inspected: {handler_path}",
        "",
    ]
    if violations:
        lines.append(
            "The following factories contain inline ORM writes for models the audit "
            "marked has_creation_code: true. This is the #1 trap the env-factory "
            "agent is warned about. You MUST call the audited creation_function "
            "(extracting it first if needs_extraction: true). See the Per-model "
            "decision tree and DI playbook in the env-factory prompt."
        )
        lines.append("")
        for model, line_no, snippet in violations:
            lines.append(f"  - {model} factory body: line {line_no}: {snippet}")
        lines.append("")
    if missing_factories:
        lines.append(
            "The following models are has_creation_code: true in the audit but have "
            "no defineFactory registration in the handler:"
        )
        for name in missing_factories:
            lines.append(f"  - {name}")
        lines.append("")
    lines.append(
        "To fix: re-run the Per-model decision tree for every failing model. If the "
        "creation function is inline in a route/framework hook, extract it into a "
        "named exported function, update entity-audit.md in place (clear "
        "needs_extraction), then call the new function from the factory."
    )
    fail("\n".join(lines))


if __name__ == "__main__":
    main()
